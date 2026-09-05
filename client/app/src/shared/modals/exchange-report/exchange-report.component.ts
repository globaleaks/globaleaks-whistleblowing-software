import {NgClass} from "@angular/common";
import {ChangeDetectorRef, Component, Input, OnDestroy, OnInit, ViewChild, inject, viewChildren} from "@angular/core";
import {FormsModule, NgForm} from "@angular/forms";
import {Router} from "@angular/router";
import {Answers, Questionnaire} from "@app/models/receiver/receiver-tip-data";
import {WhistleblowerSubmissionService} from "@app/pages/whistleblower/whistleblower-submission.service";
import {FormComponent} from "@app/pages/whistleblower/form/form.component";
import {NgFormChangeDirective} from "@app/shared/directive/ng-form-change.directive";
import {OrderByPipe} from "@app/shared/pipes/order-by.pipe";
import {FieldUtilitiesService} from "@app/shared/services/field-utilities.service";
import {UtilsService} from "@app/shared/services/utils.service";
import {HttpClient} from "@angular/common/http";
import {NgbActiveModal} from "@ng-bootstrap/ng-bootstrap";
import {TranslateModule} from "@ngx-translate/core";

/**
 * A way of filing towards another site: the channel the report is filed on
 * and what filing on it composes at this moment, the report itself or the
 * request that has to be authorized before it.
 */
interface ExchangeOption {
  id: string;
  channel_id: string;
  channel_name: string;
  stage: "report" | "request";
}

interface ExchangeTarget {
  id: number;
  name: string;
  subdomain: string;
  options: ExchangeOption[];
}

/**
 * The composition of a report filed towards another site of the platform.
 *
 * The site is chosen first, then the channel it is filed on, and the
 * questionnaire of the way chosen is the one composed: a single site or a
 * single channel is the one chosen and is not offered as a choice.
 */
@Component({
  selector: "src-exchange-report",
  templateUrl: "./exchange-report.component.html",
  standalone: true,
  imports: [FormsModule, NgClass, NgFormChangeDirective, FormComponent, TranslateModule, OrderByPipe]
})
export class ExchangeReportComponent implements OnInit, OnDestroy {
  private readonly cdr = inject(ChangeDetectorRef);
  private readonly fieldUtilitiesService = inject(FieldUtilitiesService);
  private readonly http = inject(HttpClient);
  private readonly router = inject(Router);
  protected activeModal = inject(NgbActiveModal);
  protected utilsService = inject(UtilsService);
  protected whistleblowerSubmissionService = inject(WhistleblowerSubmissionService);

  // The report handed over, where the exchange hands one over
  @Input() tipId?: string;
  @Input() title = "Transmit";
  @Input() navigateOnSuccess = true;

  @ViewChild("submissionForm") public submissionForm: NgForm;

  // The shared validation of the submissions reads the step forms as a signal
  // query: the ones of this form are declared the same way
  readonly stepForms = viewChildren<NgForm>("stepForm");

  targets: ExchangeTarget[] = [];
  selectedTenant: number | null = null;
  selectedExchange = "";
  stage = "";

  questionnaire: Questionnaire = {steps: [], answers: {}};
  answers: Answers = {};
  uploads: Record<string, any> = {};
  validate: boolean[] = [];
  navigation = 0;
  done = false;
  error = "";
  file_upload_url = "";
  private uploadWatcher: ReturnType<typeof setInterval> | null = null;

  ngOnInit(): void {
    this.file_upload_url = `${this.endpoint()}/attachment`;

    this.load();
  }

  // A transmission is composed from the list and originates from no report; a communication from a
  // report
  private endpoint(): string {
    return this.tipId ? `api/recipient/rtips/${this.tipId}/communication` :
                        "api/transmitter/transmissions";
  }

  // The destinations and the questionnaire of each come from the interface the form is composed on
  private optionsEndpoint(): string {
    return this.tipId ? `api/recipient/rtips/${this.tipId}/communication` :
                        "api/transmitter/transmissions/options";
  }

  private load(): void {
    const params: string[] = [];
    if (this.selectedTenant !== null) {
      params.push(`target_tid=${this.selectedTenant}`);
    }
    if (this.selectedExchange) {
      params.push(`exchange_id=${this.selectedExchange}`);
    }

    const query = params.length ? `?${params.join("&")}` : "";

    this.http.get(`${this.optionsEndpoint()}${query}`).subscribe((response: any) => {
      this.targets = response.targets || [];
      this.selectedTenant = response.target_tid ?? null;
      this.selectedExchange = response.exchange_id || "";
      this.stage = response.stage || "";
      this.questionnaire = response.questionnaire || {steps: [], answers: {}};
      this.answers = {};
      this.validate = [];
      this.navigation = 0;
      this.fieldUtilitiesService.onAnswersUpdate(this);
      // The response lands outside change detection (zoneless): request a
      // refresh so the destinations offered and the questionnaire are rendered
      this.cdr.markForCheck();
    });
  }

  // A single site is the one chosen: the choice is offered only where there
  // is one to make
  showTenantSelector(): boolean {
    return this.targets.length > 1;
  }

  options(): ExchangeOption[] {
    return this.targets.find(target => target.id === this.selectedTenant)?.options || [];
  }

  showChannelSelector(): boolean {
    return this.options().length > 1;
  }

  // What is composed is the request the destination authorizes before the
  // report is entered
  isRequest(): boolean {
    return this.stage === "request";
  }

  // What is composed names itself: where the destination authorizes the
  // report beforehand, what is filed here is the request of it
  modalTitle(): string {
    return this.isRequest() ? "Request" : this.title;
  }

  onTenantChange(): void {
    this.selectedExchange = "";
    this.questionnaire = {steps: [], answers: {}};
    this.load();
  }

  onExchangeChange(): void {
    this.questionnaire = {steps: [], answers: {}};
    this.load();
  }

  composing(): boolean {
    return this.selectedTenant !== null && !!this.selectedExchange &&
           this.questionnaire.steps.length > 0;
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
    return this.selectedTenant !== null;
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

    // The attachments are uploaded on demand: the report is filed only once
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
      this.performSubmission();
    }, 1000);
  }

  // Filed once every transfer completed: the watch is dropped when it fires or the composition is
  // abandoned
  private stopWatchingUploads() {
    if (this.uploadWatcher !== null) {
      clearInterval(this.uploadWatcher);
      this.uploadWatcher = null;
    }
  }

  ngOnDestroy(): void {
    this.stopWatchingUploads();
  }

  private performSubmission() {
    this.http.post(this.endpoint(), {
      target_tid: this.selectedTenant,
      exchange_id: this.selectedExchange,
      answers: this.answers
    }).subscribe({
      next: (response: any) => {
        this.activeModal.close(response);

        // The reader follows what it filed where it keeps access: a request, or a report on itself
        if (this.navigateOnSuccess && response.accessible) {
          void this.router.navigate(["reports", response.id]);
        }
      },
      error: (response: any) => {
        // The modal covers the notification of the errors of the application
        // and the reason of the failure has therefore to be reported here
        this.error = response?.error?.error_message || "Submission failed";
        this.done = false;
        // The failure lands outside change detection (zoneless): request a
        // refresh so the reason is rendered
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
