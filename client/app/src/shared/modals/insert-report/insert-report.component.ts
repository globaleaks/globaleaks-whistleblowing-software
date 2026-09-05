import {NgClass} from "@angular/common";
import {ChangeDetectorRef, Component, Input, OnDestroy, OnInit, ViewChild, inject, viewChildren} from "@angular/core";
import {FormsModule, NgForm} from "@angular/forms";
import {Answers, Questionnaire} from "@app/models/receiver/receiver-tip-data";
import {WhistleblowerSubmissionService} from "@app/pages/whistleblower/whistleblower-submission.service";
import {FormComponent} from "@app/pages/whistleblower/form/form.component";
import {ReceiptComponent} from "@app/pages/whistleblower/receipt/receipt.component";
import {NgFormChangeDirective} from "@app/shared/directive/ng-form-change.directive";
import {OrderByPipe} from "@app/shared/pipes/order-by.pipe";
import {CryptoService} from "@app/shared/services/crypto.service";
import {FieldUtilitiesService} from "@app/shared/services/field-utilities.service";
import {HttpService} from "@app/shared/services/http.service";
import {UtilsService} from "@app/shared/services/utils.service";
import {HttpClient} from "@angular/common/http";
import {NgbActiveModal} from "@ng-bootstrap/ng-bootstrap";
import {TranslateModule} from "@ngx-translate/core";
import {firstValueFrom} from "rxjs";

/** A channel of the site a report may be entered on */
interface InsertionChannel {
  id: string;
  name: string;
  provide_access_code: boolean;
}

/**
 * The composition of a report entered on the site by one of its recipients.
 *
 * The channel is chosen first and its questionnaire is the one composed: a
 * single channel is the one chosen and is not offered as a choice. What is
 * entered is a report of the site as any other; the access code it is opened
 * with is handed to the recipient that entered it only where the channel
 * provides it, and is otherwise held by no one.
 */
@Component({
  selector: "src-insert-report",
  templateUrl: "./insert-report.component.html",
  standalone: true,
  imports: [FormsModule, NgClass, NgFormChangeDirective, FormComponent, ReceiptComponent, TranslateModule, OrderByPipe]
})
export class InsertReportComponent implements OnInit, OnDestroy {
  private readonly cdr = inject(ChangeDetectorRef);
  private readonly cryptoService = inject(CryptoService);
  private readonly fieldUtilitiesService = inject(FieldUtilitiesService);
  private readonly http = inject(HttpClient);
  private readonly httpService = inject(HttpService);
  protected activeModal = inject(NgbActiveModal);
  protected utilsService = inject(UtilsService);
  protected whistleblowerSubmissionService = inject(WhistleblowerSubmissionService);

  @Input() title = "Enter a report";

  @ViewChild("submissionForm") public submissionForm: NgForm;

  // The shared validation of the submissions reads the step forms as a signal
  // query: the ones of this form are declared the same way
  readonly stepForms = viewChildren<NgForm>("stepForm");

  readonly endpoint = "api/recipient/rtips/insertion";

  channels: InsertionChannel[] = [];
  selectedChannel = "";

  questionnaire: Questionnaire = {steps: [], answers: {}};
  answers: Answers = {};
  uploads: Record<string, any> = {};
  validate: boolean[] = [];
  navigation = 0;
  done = false;
  error = "";
  receipt = "";
  // A report entered on a channel that does not provide the access code is
  // acknowledged in its place: there is no code to hand over
  submitted = false;
  file_upload_url = "";
  private uploadWatcher: ReturnType<typeof setInterval> | null = null;

  ngOnInit(): void {
    this.file_upload_url = `${this.endpoint}/attachment`;

    this.load();
  }

  private load(): void {
    const query = this.selectedChannel ? `?channel_id=${this.selectedChannel}` : "";

    this.http.get(`${this.endpoint}${query}`).subscribe((response: any) => {
      this.channels = response.channels || [];
      this.selectedChannel = response.channel_id || "";
      this.questionnaire = response.questionnaire || {steps: [], answers: {}};
      this.answers = {};
      this.validate = [];
      this.navigation = 0;
      this.fieldUtilitiesService.onAnswersUpdate(this);
      // The response lands outside change detection (zoneless): request a
      // refresh so the channels offered and the questionnaire are rendered
      this.cdr.markForCheck();
    });
  }

  // A single channel is the one chosen: the choice is offered only where
  // there is one to make
  showChannelSelector(): boolean {
    return this.channels.length > 1;
  }

  onChannelChange(): void {
    this.questionnaire = {steps: [], answers: {}};
    this.load();
  }

  composing(): boolean {
    return !!this.selectedChannel && this.questionnaire.steps.length > 0 &&
           !this.receipt && !this.submitted;
  }

  goToStep(step: number) {
    this.navigation = step;
    this.utilsService.scrollToTop();
  }

  firstStepIndex() {
    return 0;
  }

  lastStepIndex() {
    let lastEnabled = 0;
    for (let i = 0; i < this.questionnaire.steps.length; i++) {
      if (this.questionnaire.steps[i].enabled) {
        lastEnabled = i;
      }
    }

    return lastEnabled;
  }

  hasPreviousStep() {
    return this.navigation > this.firstStepIndex();
  }

  hasNextStep() {
    return this.navigation < this.lastStepIndex();
  }

  runValidation() {
    this.validate[this.navigation] = true;
    if (!this.whistleblowerSubmissionService.checkForInvalidFields(this)) {
      this.utilsService.scrollToTop();
      return false;
    }

    return true;
  }

  areReceiversSelected() {
    return !!this.selectedChannel;
  }

  uploading() {
    for (const key in this.uploads) {
      if (this.uploads[key].flowJs && this.uploads[key].flowJs.isUploading()) {
        return true;
      }
    }

    return false;
  }

  completeSubmission() {
    this.fieldUtilitiesService.onAnswersUpdate(this);
    if (!this.runValidation() || !this.composing()) {
      return;
    }

    this.done = true;
    this.error = "";

    // The attachments are uploaded on demand: the report is entered only once
    // every transfer has completed
    this.utilsService.resumeFileUploads(this.uploads);

    this.uploadWatcher = setInterval(() => {
      // The transfers advance outside change detection (zoneless): request a
      // refresh so their progress is rendered while they run
      this.cdr.markForCheck();

      if (this.uploading()) {
        return;
      }

      this.stopWatchingUploads();
      void this.performSubmission();
    }, 1000);
  }

  // The report is entered once every transfer has completed: the watch is
  // dropped as soon as it fires and whenever the composition is abandoned, so
  // that a transfer that never completes leaves no timer behind
  private stopWatchingUploads() {
    if (this.uploadWatcher !== null) {
      clearInterval(this.uploadWatcher);
      this.uploadWatcher = null;
    }
  }

  ngOnDestroy(): void {
    this.stopWatchingUploads();
  }

  private async performSubmission() {
    // The access code is composed here and the platform is told of its hash
    // alone, exactly as when a report is filed by the reporting person: what
    // The code that opens the report is handed over and kept nowhere else; without
    // provide_access_code the platform keys it
    const receipt = this.cryptoService.generateReceipt();

    const type = await firstValueFrom(
      this.httpService.requestAuthType(JSON.stringify({username: ""})));

    const hashed = type.type === "key" ?
      await this.cryptoService.hashArgon2(receipt, type.salt) : receipt;

    this.http.post(this.endpoint, {
      context_id: this.selectedChannel,
      answers: this.answers,
      receipt: hashed
    }).subscribe({
      next: (response: any) => {
        if (response?.provide_access_code) {
          this.receipt = receipt;
        } else {
          this.submitted = true;
        }
        // The outcome lands outside change detection (zoneless): request a
        // refresh so that it is rendered
        this.cdr.markForCheck();
      },
      error: (response: any) => {
        // The modal covers the notification of the errors of the application
        // and the reason of the failure has therefore to be reported here
        this.error = response?.error?.error_message || "Submission failed";
        this.done = false;
        this.cdr.markForCheck();
      }
    });
  }

  stepForm(index: number): any {
    if (index !== -1) {
      return this.stepForms().at(index);
    }
  }

  displayStepErrors(index: number): any {
    if (index !== -1) {
      const response = this.stepForm(index);
      return response ? response.invalid : false;
    }

    return false;
  }

  onFormChange(): void {
    this.fieldUtilitiesService.onAnswersUpdate(this);
  }

  onFileUpload(): void {
    this.fieldUtilitiesService.onAnswersUpdate(this);
  }
}
