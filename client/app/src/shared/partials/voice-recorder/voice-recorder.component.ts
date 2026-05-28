import {ChangeDetectorRef, Component, ElementRef, EventEmitter, Input, OnDestroy, OnInit, Output, ViewChild, inject} from "@angular/core";
import Flow from "@flowjs/flow.js";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {SubmissionService} from "@app/services/helper/submission.service";
import {Observable} from "rxjs";
import {Field} from "@app/models/resolvers/field-template-model";
import {DomSanitizer, SafeResourceUrl} from "@angular/platform-browser";
import {UtilsService} from "@app/shared/services/utils.service";
import {NgClass} from "@angular/common";
import {ControlContainer, FormsModule, NgForm} from "@angular/forms";

// Filterbank span and resolution. Log-spacing over this range gives a constant-Q filterbank
// (Q is about 10.3 at 48 bands). The band count is mostly a naturalness, CPU and anonymity
// trade-off rather than an intelligibility one: a channel vocoder is already intelligible
// with as few as about 8 bands (Shannon et al., 1995; cochlear implants use roughly 8 to 22
// channels). The audible synthetic timbre comes mainly from how far apart the sine carriers
// sit: adjacent carriers are (max/min)^(1/N) apart, about 2.5 semitones at 32 bands, 1.7 at
// 48, 1.3 at 64, so more bands sound smoother. Fewer bands also coarsen the envelope (a
// little less speaker detail is retained, which marginally helps anonymity) and cost less
// CPU. 48 bands keeps the comb of carriers from being obvious while staying lighter than 64.
// The low edge sits at 150Hz rather than 100Hz because below it there is little
// intelligibility, only rumble and F0-region energy that could leak pitch into the envelope.
const VOCODER_BAND_MIN_HZ = 150;
const VOCODER_BAND_MAX_HZ = 16000;
const VOCODER_BAND_COUNT = 48;
// Above this analysis-band centre speech is mostly noise-like (fricatives and sibilants), so
// those bands use filtered-noise carriers instead of sine carriers. The threshold is set at
// 6kHz so the 4 to 6kHz sibilant-onset region keeps harmonic (sine) carriers: noise there
// dulls consonants or adds hiss while adding no anonymity, since F0 is already destroyed and
// the formants are already warped.
const NOISE_CARRIER_THRESHOLD_HZ = 6000;
// Envelope-follower cutoff. It sits above the syllabic and transient modulation rates that
// carry intelligibility (below about 50Hz) but below every human F0 floor (a deep male voice
// is around 80Hz, vocal fry around 60Hz), so the speaker pitch cannot leak into the envelope
// and re-modulate the carrier.
const ENVELOPE_LPF_HZ = 50;
// Per-recording non-affine warp of the carrier (synthesis) frequencies. An earlier design used
// a single bilinear all-pass coefficient, which across the speech band is close to a uniform
// formant rescaling: a one-parameter map that vocal-tract-length normalization (VTLN) inverts
// with a single global factor, so it added no unlinkability. Instead the carrier axis is warped
// by a smooth, monotonic curve whose SHAPE is drawn fresh per recording (see createCarrierWarp),
// so F1, F2 and F3 move by different ratios and directions. A single-factor VTLN cannot undo a
// frequency-dependent warp, so this adds a modest amount of genuine unlinkability on top of the
// perceptual disguise; an attacker fitting a flexible (non-affine) warp could still partially
// recover it, so the real, non-reversible protection remains the vocoder destroying F0,
// excitation and intra-band phase (see the envelope and carrier design), not this warp.
//
// WARP_MAX_LOG_SHIFT bounds the per-region shift: exp(0.10) is about +/-10%, comfortably inside
// the conventional VTLN intelligibility range (+/-20%, Lee & Rose 1998). This sits below the full
// 15% to 20% male/female formant gap, trading some disguise strength for intelligibility; what
// matters for unlinkability is less the absolute shift than that F1, F2 and F3 move by DIFFERENT
// amounts (non-affine), which a single-factor VTLN cannot undo. Larger shifts start to confuse
// vowels and risk F3 collisions. With the endpoints pinned and WARP_CONTROL_POINTS - 2 interior
// control points, the warp is monotonic by construction, so band ordering is preserved and no
// carrier is pushed below the low edge or above Nyquist.
const WARP_CONTROL_POINTS = 5;
const WARP_MAX_LOG_SHIFT = 0.10;
// Section quality factors of a 4th-order Butterworth low-pass, realized as two cascaded
// biquads at the same cutoff: maximally flat passband, no resonant peak, 24dB per octave.
const BUTTERWORTH_4TH_ORDER_Q = [0.54119610, 1.30656296];
// Pre-emphasis applied to the analysis (modulator) path only, never the carriers. Speech has a
// roughly -6dB/octave spectral tilt, so the high formants F2-F4 that carry most consonant and
// vowel-identity cues sit well below F1 in energy; their band envelopes come out weak and the
// resynthesis sounds muffled. A high-shelf lift above PRE_EMPHASIS_HZ raises those envelopes, so
// the matching carriers come up and consonants sharpen. It shapes the band envelopes only, not
// the carriers, the warp or F0, so it does not weaken the anonymity. Kept modest because too much
// makes sibilants hiss; no matching de-emphasis is applied, so the output is intentionally a
// little brighter, which reads as clearer.
const PRE_EMPHASIS_HZ = 1500;
const PRE_EMPHASIS_GAIN_DB = 6;

// Builds the log-spaced analysis bands, which approximate the perceptual (Bark/ERB)
// frequency resolution of hearing. The log span is divided by numBands (not numBands - 1)
// so the bands tile [startFreq, endFreq] exactly and the highest band centre stays below
// endFreq and Nyquist; dividing by numBands - 1 lets the last band overshoot and
// BiquadFilterNode would then clamp its frequency to Nyquist. Each band centre is the
// geometric mean of the edges, the natural centre on a log axis, which gives a constant
// fractional bandwidth and therefore a constant Q.
function generateVocoderBands(startFreq: number, endFreq: number, numBands: number): { freq: number; Q: number }[] {
  const vocoderBands: { freq: number; Q: number }[] = [];
  const logStep: number = Math.log(endFreq / startFreq) / numBands;

  for (let i = 0; i < numBands; i++) {
    const lo: number = startFreq * Math.exp(i * logStep);
    const hi: number = startFreq * Math.exp((i + 1) * logStep);
    const fc: number = Math.sqrt(hi * lo);
    const bw: number = hi - lo;
    const Q: number = fc / bw;

    vocoderBands.push({freq: fc, Q: Q});
  }

  return vocoderBands;
}

// Full-wave rectifier curve used by the WaveShaperNode of each band to turn the
// band-limited signal into something the envelope low-pass can smooth into an amplitude.
function generateRectifierCurve(): Float32Array {
  const rectifierCurve = new Float32Array(65536);
  for (let i = -32768; i < 32768; i++)
    rectifierCurve[i + 32768] = ((i > 0) ? i : -i) / 32768;
  return rectifierCurve;
}

// Builds the per-recording carrier-frequency warp described above WARP_CONTROL_POINTS, returning
// a function that maps an analysis-band centre to a warped carrier centre. The warp lives on the
// log-frequency axis (the perceptual axis, where a constant ratio is a constant interval):
// WARP_CONTROL_POINTS control points are spread evenly across the band span, the two endpoints
// pinned to zero shift and each interior point given an independent random log shift in
// +/-WARP_MAX_LOG_SHIFT. Between control points the shift is interpolated with smoothstep
// (3t^2 - 2t^3), which is flat at the knots, so the curve is smooth (C1); with shifts this small
// relative to the control-point spacing the resulting map u -> u + shift(u) stays strictly
// increasing, so adjacent carriers never cross. Pinning the endpoints keeps the lowest and
// highest carriers in place (none pushed below the low edge or past Nyquist) and warps only the
// interior formant region. The map is defined purely in Hz, independent of the sample rate.
function createCarrierWarp(minHz: number, maxHz: number): (freq: number) => number {
  const uMin = Math.log(minHz);
  const uMax = Math.log(maxHz);
  const shifts: number[] = [];
  for (let k = 0; k < WARP_CONTROL_POINTS; k++) {
    const pinned = k === 0 || k === WARP_CONTROL_POINTS - 1;
    shifts.push(pinned ? 0 : (Math.random() * 2 - 1) * WARP_MAX_LOG_SHIFT);
  }
  return (freq: number): number => {
    const u = Math.log(freq);
    let x = (u - uMin) / (uMax - uMin);
    x = x < 0 ? 0 : (x > 1 ? 1 : x);
    const seg = x * (WARP_CONTROL_POINTS - 1);
    let k = Math.floor(seg);
    if (k > WARP_CONTROL_POINTS - 2) {
      k = WARP_CONTROL_POINTS - 2;
    }
    const t = seg - k;
    const s = t * t * (3 - 2 * t);
    const shift = shifts[k] + (shifts[k + 1] - shifts[k]) * s;
    return Math.exp(u + shift);
  };
}

// Single white-noise buffer shared by every noise-carrier band, to avoid allocating one
// buffer per band.
function generateNoiseBuffer(audioContext: AudioContext): AudioBuffer {
  const bufferSize = 2 * audioContext.sampleRate;
  const noiseBuffer = audioContext.createBuffer(1, bufferSize, audioContext.sampleRate);
  const data = noiseBuffer.getChannelData(0);
  for (let s = 0; s < bufferSize; s++) {
    data[s] = Math.random() * 2 - 1;
  }
  return noiseBuffer;
}

// Each noise carrier reads the shared buffer from a different start offset so the carriers
// are mutually decorrelated. Without the offset the overlapping high bands would extract
// the same in-phase noise and sum coherently, colouring the spectrum around the crossovers.
function generateNoiseSource(audioContext: AudioContext, noiseBuffer: AudioBuffer, offset: number): AudioBufferSourceNode {
  const noise = audioContext.createBufferSource();
  noise.buffer = noiseBuffer;
  noise.loop = true;
  noise.start(0, offset);
  return noise;
}

// Sine carrier with a random starting phase. A plain OscillatorNode sine always starts at
// phase 0, so every band's carrier rises through zero together and their crests realign
// periodically; on a broadband transient (a plosive) the bands then sum near-coherently and
// the peak approaches the sum of the band amplitudes (about N) rather than their root-sum-
// square (about sqrt(N)), which is what drives the limiter. Giving each carrier a random
// phase decorrelates the crests and lowers the peak factor, so the limiter engages less and
// the synthesis stays cleaner. Phase is inaudible in steady state (Ohm's phase law), so this
// does not change the timbre or the anonymity, only the crest factor. Web Audio exposes no
// phase on OscillatorNode, so the phase is encoded in a single-harmonic PeriodicWave:
// A*sin(wt + p) = sin(p)*cos(wt) + cos(p)*sin(wt), where the real array multiplies the cosine
// and the imag array the sine. The coefficient magnitude sqrt(sin^2 + cos^2) is 1, so the
// carrier keeps unit amplitude and the sineCarrierRMS used for noise level-matching holds;
// disableNormalization keeps that exact.
function createPhaseRandomizedSineCarrier(audioContext: AudioContext, freq: number): OscillatorNode {
  const phase = Math.random() * 2 * Math.PI;
  const real = new Float32Array([0, Math.sin(phase)]);
  const imag = new Float32Array([0, Math.cos(phase)]);
  const wave = audioContext.createPeriodicWave(real, imag, {disableNormalization: true});
  const osc = audioContext.createOscillator();
  osc.setPeriodicWave(wave);
  osc.frequency.value = freq;
  osc.start();
  return osc;
}

// One 2nd-order (biquad) low-pass section. Two of these in cascade, at the Butterworth
// section Qs, form the 4th-order envelope follower.
function createLowpass(audioContext: AudioContext, freq: number, Q: number): BiquadFilterNode {
  const filter = audioContext.createBiquadFilter();
  filter.type = 'lowpass';
  filter.frequency.value = freq;
  filter.Q.value = Q;
  return filter;
}

// Channel vocoder used for real-time, client-side speaker anonymization.
//
// The method is a classic analysis and synthesis channel vocoder (Dudley, 1939): the input
// is split into frequency bands, the slow amplitude envelope of each band is measured, and
// that envelope is used to drive an independent carrier in the same band. Re-synthesizing
// speech from band envelopes alone discards the fine spectral and temporal structure of the
// original excitation, which is what makes the operation largely one-way.
//
// Per band:
//   Analysis:  input -> bandpass -> full-wave rectifier -> 4th-order Butterworth low-pass,
//              giving the band amplitude envelope
//   Synthesis: a fixed-frequency carrier (a sine below 6kHz, band-limited noise above 6kHz)
//              placed at a frequency-warped band centre
//   Output:    carrier scaled by the envelope, summed across all bands, then limited
//
// Design choices and their rationale:
//   - Pitch (F0) removal. The carriers run at fixed frequencies and the envelope follower
//     cuts off below the human F0 floor (see ENVELOPE_LPF_HZ), so the speaker pitch and the
//     glottal excitation are not reconstructed. This is the main difference from LPC- or
//     McAdams-style methods (Patino et al., 2021), which keep and re-use the original
//     residual and so leak pitch and prosody.
//   - Formant disguise. The analysis filters stay at the original band centres for a correct
//     spectral decomposition; only the carrier centres are warped, which relocates the
//     spectral energy and so moves the formants. The warp is a smooth, monotonic, non-affine
//     curve drawn fresh per recording (see createCarrierWarp and WARP_CONTROL_POINTS), so the
//     formants shift by a frequency-dependent amount that a single-factor VTLN cannot fully
//     undo. It is still a secondary measure: the anonymity comes from the vocoder destroying
//     F0 and excitation, not from relocating the formants.
//   - Carrier choice. Sine carriers below 6kHz preserve a harmonic backbone for
//     intelligibility; decorrelated band-limited noise above 6kHz matches the already
//     noise-like fricatives and sibilants and is level-matched to the sine carriers so the
//     crossover is not audible.
//   - Sample rate and band count are kept modest (see initAudioContext and
//     VOCODER_BAND_COUNT) so the whole graph stays affordable on mobile devices.
//
// Known limitations. This is best-effort signal-processing anonymization and should be
// presented to users as raising the bar, not as a guarantee that the speaker cannot be
// identified. It is effective against human recognition and against naive automatic speaker
// verification, but it is only moderately protective against a strong, informed attacker,
// much like the VoicePrivacy McAdams baseline (system B2 in Tomashenko et al., 2024). The
// non-affine formant warp resists single-factor vocal-tract-length normalization, but an
// attacker fitting a flexible frequency-dependent warp could still partially undo it, and
// speaking rate, rhythm and other prosodic habits still carry identity. Stronger anonymization
// (neural x-vector or ASR-to-TTS pipelines) is not currently feasible in real time in the browser.
//
// References:
//   Dudley (1939), "Remaking Speech", J. Acoust. Soc. Am. 11(2).
//   Shannon, Zeng, Kamath, Wygonski & Ekelid (1995), "Speech Recognition with Primarily
//     Temporal Cues", Science 270(5234).
//   Lee & Rose (1998), "A Frequency Warping Approach to Speaker Normalization", IEEE TSAP 6(1).
//   Patino, Tomashenko, Todisco, Nautsch & Evans (2021), "Speaker Anonymisation Using the
//     McAdams Coefficient", Interspeech.
//   Tomashenko et al. (2024), "The VoicePrivacy 2024 Challenge Evaluation Plan",
//     arXiv:2404.02677.
function anonymizeSpeaker(audioContext: AudioContext) {
  const input: GainNode = audioContext.createGain();
  const output: GainNode = audioContext.createGain();
  input.gain.value = output.gain.value = 1;
  // The bands sum into mixBus and a limiter guards the output against clipping: even with the
  // carriers given random starting phases (see createPhaseRandomizedSineCarrier, which lowers
  // the peak factor), a loud broadband transient can still drive several bands up at once and
  // sum past full scale. It only engages above -3dBFS, so normal levels pass through untouched.
  const mixBus: GainNode = audioContext.createGain();
  const limiter: DynamicsCompressorNode = audioContext.createDynamicsCompressor();
  limiter.threshold.value = -3;
  limiter.knee.value = 0;
  limiter.ratio.value = 20;
  limiter.attack.value = 0.003;
  limiter.release.value = 0.25;
  mixBus.connect(limiter);
  limiter.connect(output);
  const vocoderBands = generateVocoderBands(VOCODER_BAND_MIN_HZ, VOCODER_BAND_MAX_HZ, VOCODER_BAND_COUNT);
  const noiseBuffer = generateNoiseBuffer(audioContext);
  const noiseBufferRMS = 1 / Math.sqrt(3);
  const sineCarrierRMS = Math.SQRT1_2;
  const rectifierCurve = generateRectifierCurve();
  // One non-affine warp shape, drawn once and shared by every band of this recording.
  const warpCarrier = createCarrierWarp(VOCODER_BAND_MIN_HZ, VOCODER_BAND_MAX_HZ);
  // High-shelf pre-emphasis on the analysis path (see PRE_EMPHASIS_HZ): the band filters tap this
  // node, not input directly, so the lift shapes the envelopes that drive the carriers without
  // touching the carriers themselves.
  const preEmphasis: BiquadFilterNode = audioContext.createBiquadFilter();
  preEmphasis.type = 'highshelf';
  preEmphasis.frequency.value = PRE_EMPHASIS_HZ;
  preEmphasis.gain.value = PRE_EMPHASIS_GAIN_DB;
  input.connect(preEmphasis);

  for (let i = 0; i < vocoderBands.length; i++) {
    const Q = vocoderBands[i].Q;
    const warpedFreq = warpCarrier(vocoderBands[i].freq);

    let carrier: AudioNode;
    let carrierLevel: number;
    if (vocoderBands[i].freq > NOISE_CARRIER_THRESHOLD_HZ) {
      const noiseOffset = (i / vocoderBands.length) * noiseBuffer.duration;
      const noiseSource = generateNoiseSource(audioContext, noiseBuffer, noiseOffset);
      const carrierBandFilter: BiquadFilterNode = audioContext.createBiquadFilter();
      carrierBandFilter.type = 'bandpass';
      carrierBandFilter.frequency.value = warpedFreq;
      carrierBandFilter.Q.value = Q;
      noiseSource.connect(carrierBandFilter);
      carrier = carrierBandFilter;
      // Bandpass-filtered noise has RMS = bufferRMS * sqrt(pi*fc/(Q*fs)), the noise-
      // equivalent bandwidth of a biquad; scale it up to the sine level so the sine to
      // noise crossover is seamless. This is an estimate, so fine-tune by ear if the
      // fricatives sound too hot or too dull.
      const noiseRMS = noiseBufferRMS * Math.sqrt(Math.PI * warpedFreq / (Q * audioContext.sampleRate));
      carrierLevel = sineCarrierRMS / noiseRMS;
    } else {
      carrier = createPhaseRandomizedSineCarrier(audioContext, warpedFreq);
      carrierLevel = 1;
    }

    // Modulator: extract the amplitude envelope of the input in this band
    const modulatorBandFilter: BiquadFilterNode = audioContext.createBiquadFilter();
    modulatorBandFilter.type = 'bandpass';
    modulatorBandFilter.frequency.value = vocoderBands[i].freq;
    modulatorBandFilter.Q.value = Q;
    const rectifier: WaveShaperNode = audioContext.createWaveShaper();
    rectifier.curve = rectifierCurve as Float32Array<ArrayBuffer>;
    // Envelope follower: a 4th-order Butterworth low-pass (two cascaded biquads, 24dB per
    // octave) smooths the rectified signal into a clean amplitude envelope. See
    // ENVELOPE_LPF_HZ and BUTTERWORTH_4TH_ORDER_Q for the cutoff and anonymity rationale.
    const envelopeLowpass1 = createLowpass(audioContext, ENVELOPE_LPF_HZ, BUTTERWORTH_4TH_ORDER_Q[0]);
    const envelopeLowpass2 = createLowpass(audioContext, ENVELOPE_LPF_HZ, BUTTERWORTH_4TH_ORDER_Q[1]);
    // bandGain starts at 0; the envelope modulates it through the gain AudioParam
    const bandGain: GainNode = audioContext.createGain();
    bandGain.gain.value = 0;
    // Signal chain: input -> pre-emphasis -> bandpass -> rectifier -> LPF -> LPF -> envelope -> gain control
    preEmphasis.connect(modulatorBandFilter);
    modulatorBandFilter.connect(rectifier);
    rectifier.connect(envelopeLowpass1);
    envelopeLowpass1.connect(envelopeLowpass2);
    // Carrier level normalization: sine carriers are already at unity (carrierLevel === 1),
    // so the envelope drives bandGain.gain directly; only noise carriers need a scaling node
    // to match the sine level, which saves one GainNode per sine band.
    if (carrierLevel !== 1) {
      const postRectifierGain: GainNode = audioContext.createGain();
      postRectifierGain.gain.value = carrierLevel;
      envelopeLowpass2.connect(postRectifierGain);
      postRectifierGain.connect(bandGain.gain);
    } else {
      envelopeLowpass2.connect(bandGain.gain);
    }
    carrier.connect(bandGain);
    bandGain.connect(mixBus);
  }
  return {input: input, output: output};
}

/**
 * VoiceRecorderComponent provides client-side speaker anonymization for the
 * whistleblower voice message feature.
 *
 * Capture, anonymization and encoding all happen in the browser: the microphone
 * signal is passed through a Web Audio channel vocoder and only the processed
 * stream is handed to the MediaRecorder, so the original voice never leaves the
 * device. The vocoder graph is built in anonymizeSpeaker, where the method, the
 * design choices and the known limitations are documented in full.
 */
@Component({
    selector: "src-voice-recorder",
    templateUrl: "./voice-recorder.component.html",
    viewProviders: [{ provide: ControlContainer, useExisting: NgForm }],
    standalone: true,
    imports: [NgClass, FormsModule]
})
export class VoiceRecorderComponent implements OnInit, OnDestroy {
  private cd = inject(ChangeDetectorRef);
  private utilsService = inject(UtilsService);
  private sanitizer = inject(DomSanitizer);
  protected authenticationService = inject(AuthenticationService);
  private submissionService = inject(SubmissionService);

  @Input() uploads: any;
  @Input() field: Field;
  @Input() fileUploadUrl: string;
  @Input() entryIndex: number;
  @Input() fieldEntry: string;
  @Input() entry: any;
  _fakeModel: string;
  fileInput: string;
  seconds = 0;
  activeButton: string | null = null;
  // Stays true from the start of recording until the blob has been committed to the flow in
  // onRecorderStop (or discarded in deleteRecording), not just until capture stops. This keeps
  // the field invalid through the asynchronous MediaRecorder finalization, so a stop followed
  // by an immediate submit cannot send the report without the not-yet-attached recording.
  isRecording = false;
  audioPlayer: boolean | string | null = null;
  mediaRecorder: MediaRecorder | null = null;
  private micStream: MediaStream | null = null;
  recording_blob: any = null;
  flow: Flow;
  private secondsTracker: ReturnType<typeof setInterval> | null = null;
  startTime: number;
  stopButton: boolean;
  recordButton: boolean;

  @Output() notifyFileUpload: EventEmitter<any> = new EventEmitter<any>();
  private audioContext: AudioContext|null;
  private audioExt: string = 'audio.webm';
  iframeUrl: SafeResourceUrl;
  @ViewChild("viewer") viewerFrame: ElementRef;

  ngOnDestroy(): void {
    if (this.secondsTracker) {
      clearInterval(this.secondsTracker);
      this.secondsTracker = null;
    }

    if (this.micStream) {
      this.micStream.getTracks().forEach(track => track.stop());
      this.micStream = null;
    }

    if (this.mediaRecorder) {
      this.mediaRecorder.stop();
      this.mediaRecorder = null;
    }

    if (this.audioContext && this.audioContext.state !== 'closed') {
      this.audioContext.close();
      this.audioContext = null;
    }
  }

  ngOnInit(): void {
    this.iframeUrl = this.sanitizer.bypassSecurityTrustResourceUrl("viewer/index.html");
    this.fileInput = this.field ? this.field.id : "status_page";
    // Honour the URL provided by the host form (the initial submission posts to
    // submission/attachment, an existing tip's additional questionnaire to wbtip/wbfiles).
    // Hardcoding the submission endpoint sent additional-questionnaire recordings to the wrong
    // handler, where they were buffered for a never-finalized submission instead of attached.
    this.fileUploadUrl = this.fileUploadUrl || "api/whistleblower/submission/attachment";

    this.initAudioContext()
  }

  private initAudioContext() {
    const AudioContextCtor = window.AudioContext || (window as any).webkitAudioContext;
    // Use the hardware default sample rate. A lower custom rate (e.g. 32kHz) would cut the
    // vocoder's CPU on mobile, but it is not portable: Firefox does not resample a hardware-rate
    // microphone into a custom-rate context and throws when the mic is connected, and Safari
    // before 15.4 rejects a custom rate outright. Matching the hardware rate keeps the graph
    // working on every engine. The band centres and the carrier warp are fixed in Hz and the
    // noise-carrier math reads audioContext.sampleRate at run time, so they adapt to whatever
    // rate the hardware grants (its Nyquist is always well above the 16kHz top band).
    this.audioContext = new AudioContextCtor();
  }

  triggerRecording(fileId: string): void {
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
      this.activeButton = "record";

      // autoGainControl and echoCancellation are on by default for getUserMedia({audio:true})
      // but only hurt here: AGC pumps the amplitude envelope the vocoder relies on, echo
      // cancellation distorts it, and neither helps anonymity. noiseSuppression is kept for
      // privacy (it removes location-identifying background sound), not for voice anonymity.
      navigator.mediaDevices.getUserMedia({audio: {autoGainControl: false, echoCancellation: false, noiseSuppression: true}})
        .then((stream) => {
          this.startRecording(fileId, stream).then();
        })
        .catch(() => {
          this.activeButton = null;
        });
    }
  }

  startRecording = async (fileId: string, stream: MediaStream) => {
    this.isRecording = true;
    this.audioPlayer = '';
    this.activeButton = 'record';
    this.seconds = 0;
    this.startTime = Date.now();
    this.flow = this.utilsService.getFlowInstance();
    this.flow.opts.target =  this.fileUploadUrl;
    this.flow.opts.singleFile =  this.field !== undefined && !this.field.multi_entry;
    const useWebm = MediaRecorder.isTypeSupported('audio/webm;codecs=opus');
    const audioMimeType = useWebm ? 'audio/webm;codecs=opus' : undefined;
    this.audioExt = useWebm ? 'audio.webm' : 'audio.mp4';
    this.flow.opts.query = {type: this.audioExt, reference_id: fileId};

    this.secondsTracker = setInterval(() => {
      this.seconds += 1;
      if (this.seconds >= parseInt(this.field.attrs.max_len.value)) {
        if (this.secondsTracker) {
          clearInterval(this.secondsTracker);
          this.secondsTracker = null;
        }
        this.stopRecording().subscribe();
      }
      this.cd.markForCheck();
    }, 1000);

    this.micStream = stream;

    if (!this.audioContext || this.audioContext.state === 'closed') {
      this.initAudioContext();
    }

    if(this.audioContext){
      // iOS Safari (and Chrome under the autoplay policy) start a context created outside a
      // user gesture in the 'suspended' state; without resume() the graph never runs and the
      // recording is silent. resume() must happen here, in the gesture-initiated record flow.
      if (this.audioContext.state === 'suspended') {
        await this.audioContext.resume();
      }
      const mediaStreamDestination = this.audioContext.createMediaStreamDestination();
      const source = this.audioContext.createMediaStreamSource(stream);
      const anonymizationFilter = anonymizeSpeaker(this.audioContext);
      source.connect(anonymizationFilter.input);
      anonymizationFilter.output.connect(mediaStreamDestination);

      this.mediaRecorder = new MediaRecorder(mediaStreamDestination.stream,
        audioMimeType ? { mimeType: audioMimeType } : undefined);
      this.mediaRecorder.onstop = () => {
        this.onRecorderStop().subscribe();
      };
      this.mediaRecorder.ondataavailable = this.onRecorderDataAvailable.bind(this);
      this.mediaRecorder.start();
    }
  };

  onRecorderDataAvailable = (e: BlobEvent) => {
    this.recording_blob = e.data;
    this.recording_blob.name = this.audioExt;
    this.recording_blob.relativePath = this.audioExt;
  };


  stopRecording(): Observable<void> {
    return new Observable<void>((observer) => {
      if (this.micStream) {
        this.micStream.getTracks().forEach(track => track.stop());
        this.micStream = null;
      }

      if (this.mediaRecorder) {
        this.mediaRecorder.stop();
      }

      this.recordButton = false;
      this.stopButton = true;
      this.activeButton = null;

      if (this.secondsTracker) {
        clearInterval(this.secondsTracker);
      }
      this.secondsTracker = null;

      if (this.seconds < parseInt(this.field.attrs.min_len.value)) {
        this.deleteRecording();
        observer.complete();
        return;
      }

      if (this.audioContext && this.audioContext.state !== 'closed') {
        this.audioContext.close();
        this.audioContext = null;
      }
      observer.next();
      observer.complete();
    });
  }

  onStop(): void {
    this.stopRecording().subscribe();
  }

  onRecorderStop(): Observable<void> {
    return new Observable<void>((observer) => {
      this.flow.files = [];

      if (Object.prototype.hasOwnProperty.call(this.uploads, this.fileInput)) {
        delete this.uploads[this.fileInput];
      }

      if (this.seconds >= parseInt(this.field.attrs.min_len.value) && this.seconds <= parseInt(this.field.attrs.max_len.value)) {
        this._fakeModel = "audio";
        this.flow.addFile(this.recording_blob);
        window.addEventListener("message", (message: MessageEvent) => {
          const iframe = this.viewerFrame.nativeElement;
          if (message.source !== iframe.contentWindow) {
            return;
          }
          const data = {
            tag: "audio",
            blob: this.recording_blob,
          };
          iframe.contentWindow.postMessage(data, "*");
        }, { once: true });

        this.audioPlayer = true;
        (this.flow as any).field = this.field;
        this.uploads[this.fileInput] = this.flow;
        this.submissionService.setSharedData(this.flow);
        this.notifyFileUpload.emit(this.uploads);
      }

      this.isRecording = false;
      this.cd.detectChanges();
      observer.complete();
    });
  }

  deleteRecording(): void {
    this.isRecording = false;
    this.audioPlayer = false;
    this._fakeModel = "";
    if (this.flow) {
      this.flow.cancel();
    }
    this.micStream = null;
    this.mediaRecorder = null;
    this.seconds = 0;
    this.audioPlayer = null;
    if (this.audioContext && this.audioContext.state !== 'closed') {
      this.audioContext.close();
      this.audioContext = null;
    }
    this.initAudioContext()
    this.submissionService.setSharedData(null);
    delete this.uploads[this.fileInput];
  }

  protected readonly parseInt = parseInt;
}
