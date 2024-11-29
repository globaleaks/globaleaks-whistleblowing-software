import {ChangeDetectorRef, Component, ElementRef, EventEmitter, Input, OnInit, Output, ViewChild, inject} from "@angular/core";
import * as Flow from "@flowjs/flow.js";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {SubmissionService} from "@app/services/helper/submission.service";
import {Observable} from "rxjs";
import {Field} from "@app/models/resolvers/field-template-model";
import {DomSanitizer, SafeResourceUrl} from "@angular/platform-browser";
import {UtilsService} from "@app/shared/services/utils.service";
import {NgClass} from "@angular/common";
import {ControlContainer, FormsModule, NgForm} from "@angular/forms";

@Component({
    selector: "src-voice-recorder",
    templateUrl: "./voice-recorder.component.html",
    viewProviders: [{ provide: ControlContainer, useExisting: NgForm }],
    standalone: true,
    imports: [NgClass, FormsModule]
})
export class VoiceRecorderComponent implements OnInit {
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
  seconds: number = 0;
  activeButton: string | null = null;
  isRecording: boolean = false;
  audioPlayer: boolean | string | null = null;
  mediaRecorder: MediaRecorder | null = null;
  recording_blob: any = null;
  flow: Flow;
  private secondsTracker: ReturnType<typeof setInterval> | null = null;
  startTime: number;
  stopButton: boolean;
  recordButton: boolean;
  chunks: never[];

  @Output() notifyFileUpload: EventEmitter<any> = new EventEmitter<any>();
  private audioContext: AudioContext|null;
  iframeUrl: SafeResourceUrl;
  @ViewChild("viewer") viewerFrame: ElementRef;

  ngOnInit(): void {
    this.iframeUrl = this.sanitizer.bypassSecurityTrustResourceUrl("viewer/index.html");
    this.fileInput = this.field ? this.field.id : "status_page";
    this.fileUploadUrl="api/whistleblower/submission/attachment";

    this.initAudioContext()
  }

  private initAudioContext() {
    this.audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
  }

  triggerRecording(fileId: string): void {
    this.activeButton = "record";

    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
      navigator.mediaDevices.getUserMedia({audio: true})
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
    this.flow.opts.query = {type: "audio.webm", reference_id: fileId};

    this.secondsTracker = setInterval(() => {
      this.seconds += 1;
      if (this.seconds >= parseInt(this.field.attrs.max_len.value)) {
        this.isRecording = false;
        if (this.secondsTracker) {
          clearInterval(this.secondsTracker);
          this.secondsTracker = null;
        }
        this.stopRecording().subscribe();
      }
    }, 1000);

    this.enableNoiseSuppression(stream).subscribe();
    if(this.audioContext){
      const mediaStreamDestination = this.audioContext.createMediaStreamDestination();
      const source = this.audioContext.createMediaStreamSource(stream);
      const anonymizationFilter = this.anonymizeSpeaker(this.audioContext);
      source.connect(anonymizationFilter.input);
      anonymizationFilter.output.connect(mediaStreamDestination);

      source.connect(anonymizationFilter.input);
      anonymizationFilter.output.connect(mediaStreamDestination);

      const recorder = new MediaRecorder(mediaStreamDestination.stream);
      recorder.onstop = () => {
        this.onRecorderStop().subscribe();
      };
      recorder.ondataavailable = this.onRecorderDataAvailable.bind(this);
      recorder.start();

      this.mediaRecorder = new MediaRecorder(stream);
      this.mediaRecorder.onstop = () => {
        recorder.stop();
      };

      this.mediaRecorder.start();
    }
  };

  onRecorderDataAvailable = (e: BlobEvent) => {
    this.recording_blob = e.data;
    this.recording_blob.name = "audio.webm";
    this.recording_blob.relativePath = "audio.webm";
  };


  stopRecording(): Observable<void> {
    return new Observable<void>((observer) => {
      if (this.mediaRecorder) {
        const tracks = this.mediaRecorder.stream.getTracks();
        tracks.forEach((track) => {
          track.stop();
        });
        this.mediaRecorder.stop();
      }

      this.isRecording = false;
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

      if (this.mediaRecorder && (this.mediaRecorder.state === 'recording' || this.mediaRecorder.state === 'paused')) {
        this.mediaRecorder.stop();
      }

      if (this.audioContext) {
        this.audioContext.close();
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
        this.uploads[this.fileInput] = this.flow;
        this.submissionService.setSharedData(this.flow);
        this.notifyFileUpload.emit(this.uploads);

        if (this.entry) {
          if (!this.entry.files) {
            this.entry.files = [];
          }
          this.entry.files.push(this.recording_blob.uniqueIdentifier);
        }
      }

      this.cd.detectChanges();
      observer.complete();
    });
  }

  deleteRecording(): void {
    this.audioPlayer = false;
    this._fakeModel = "";
    if (this.flow) {
      this.flow.cancel();
    }
    this.chunks = [];
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
    if (this.entry && this.entry.files) {
      delete this.entry.files;
    }
  }

  enableNoiseSuppression(stream: MediaStream): Observable<void> {
    return new Observable<void>((observer) => {
      const supportedConstraints = navigator.mediaDevices.getSupportedConstraints();

      if ("noiseSuppression" in supportedConstraints) {
        const settings = {noiseSuppression: true};

        stream.getAudioTracks().forEach(track => {
          track.applyConstraints(settings).then();
        });

        observer.complete();
      }
    });
  }

  private generateVocoderBands(startFreq: number, endFreq: number, numBands: number): { freq: number; Q: number }[] {
    const vocoderBands: { freq: number; Q: number }[] = [];
    const logStep: number = Math.log(endFreq / startFreq) / (numBands - 1);

    for (let i = 0; i < numBands; i++) {
      const lo: number = startFreq * Math.exp(i * logStep);
      const hi: number = startFreq * Math.exp((i + 1) * logStep);
      const fc: number = (hi + lo) / 2;
      const bw: number = hi - lo;
      const Q: number = fc / bw;

      vocoderBands.push({freq: fc, Q: Q});
    }

    return vocoderBands;
  }

  private generateRectifierCurve(): Float32Array {
    const rectifierCurve = new Float32Array(65536);
    for (let i = -32768; i < 32768; i++)
      rectifierCurve[i + 32768] = ((i > 0) ? i : -i) / 32768;
    return rectifierCurve;
  }

  public anonymizeSpeaker(audioContext: AudioContext) {
    const input: GainNode = audioContext.createGain();
    const output: GainNode = audioContext.createGain();
    input.gain.value = output.gain.value = 1;
    const vocoderBands = this.generateVocoderBands(100, 16000, 128);
    const pitchShift = -1/12 * Math.random();

    for (let i = 0; i < vocoderBands.length; i++) {
      const carrier: OscillatorNode = audioContext.createOscillator();
      carrier.frequency.value = vocoderBands[i].freq * Math.pow(2, pitchShift - (1/12 * Math.random()));
      const modulatorBandFilter: BiquadFilterNode = audioContext.createBiquadFilter();
      modulatorBandFilter.type = 'bandpass';
      modulatorBandFilter.frequency.value = vocoderBands[i].freq;
      modulatorBandFilter.Q.value = vocoderBands[i].Q;
      const rectifier: WaveShaperNode = audioContext.createWaveShaper();
      rectifier.curve = this.generateRectifierCurve();
      const postRectifierBandFilter: BiquadFilterNode = audioContext.createBiquadFilter();
      postRectifierBandFilter.type = 'lowpass';
      postRectifierBandFilter.frequency.value = 20;
      postRectifierBandFilter.gain.value = 1;
      const postRectifierGain: GainNode = audioContext.createGain();
      postRectifierGain.gain.value = 1;
      const bandGain: GainNode = audioContext.createGain();
      bandGain.gain.value = 0;
      input.connect(modulatorBandFilter);
      modulatorBandFilter.connect(rectifier);
      rectifier.connect(postRectifierGain);
      postRectifierGain.connect(bandGain.gain);

      if (carrier) carrier.connect(bandGain);
      if (bandGain) bandGain.connect(output);

      if (carrier) carrier.start();
    }
    return {input: input, output: output};
  }


  protected readonly parseInt = parseInt;
}

