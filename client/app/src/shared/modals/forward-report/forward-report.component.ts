import {NgClass} from "@angular/common";
import {Component, Input, OnDestroy, OnInit, QueryList, ViewChild, ViewChildren, inject} from "@angular/core";
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

interface ForwardTenant {
  id: number;
  name: string;
  subdomain: string;
}

@Component({
  selector: "src-forward-report",
  templateUrl: "./forward-report.component.html",
  standalone: true,
  imports: [FormsModule, NgClass, NgFormChangeDirective, FormComponent, TranslateModule, OrderByPipe]
})
export class ForwardReportComponent implements OnInit, OnDestroy {
  private fieldUtilitiesService = inject(FieldUtilitiesService);
  private http = inject(HttpClient);
  private router = inject(Router);
  protected activeModal = inject(NgbActiveModal);
  protected utilsService = inject(UtilsService);
  protected whistleblowerSubmissionService = inject(WhistleblowerSubmissionService);

  @Input() tipId?: string;
  @Input() tenants: ForwardTenant[] = [];
  @Input() questionnaire: Questionnaire;
  @Input() endpoint = "forward";
  @Input() title = "Forward";
  @Input() navigateOnSuccess = true;
  @Input() showTenantSelector = true;

  @ViewChild("submissionForm") public submissionForm: NgForm;
  @ViewChildren("stepForm") stepForms: QueryList<NgForm>;

  answers: Answers = {};
  uploads: Record<string, any> = {};
  validate: boolean[] = [];
  navigation = 0;
  selectedTenant: number | null = null;
  done = false;
  error = "";
  file_upload_url = "";
  private uploadWatcher: ReturnType<typeof setInterval> | null = null;

  ngOnInit(): void {
    // The attachments of a forward are uploaded on the report being forwarded
    // and are registered on the report created by the forward
    if (this.tipId && this.endpoint === "forward") {
      this.file_upload_url = `api/recipient/rtips/${this.tipId}/forward/attachment`;
    }

    // The questionnaire presented is the one of the tenant receiving the
    // report, so the target is chosen before it: the selection starts empty
    // and the questionnaire appears with it. Where the selector is not offered
    // the target is already determined and is kept.
    if (this.showTenantSelector) {
      this.selectedTenant = null;
      this.questionnaire = {steps: [], answers: {}};
    } else if (this.selectedTenant === null) {
      this.selectedTenant = this.tenants.length ? this.tenants[0].id : null;
    }

    this.fieldUtilitiesService.onAnswersUpdate(this);
  }

  onTenantChange(): void {
    // The report is filed on the channel designated by the tenant receiving it
    // and it is therefore its questionnaire that has to be presented
    if (this.selectedTenant === null) {
      this.questionnaire = {steps: [], answers: {}};
      this.answers = {};
      this.validate = [];
      this.navigation = 0;
      return;
    }

    if (!this.tipId) {
      return;
    }

    this.http.get(`api/recipient/rtips/${this.tipId}/${this.endpoint}?target_tid=${this.selectedTenant}`)
      .subscribe((response: any) => {
        this.questionnaire = response.questionnaire;
        this.answers = {};
        this.validate = [];
        this.navigation = 0;
        this.fieldUtilitiesService.onAnswersUpdate(this);
      });
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
    if (!this.runValidation() || this.selectedTenant === null) {
      return;
    }

    this.done = true;
    this.error = "";

    // The attachments are uploaded on demand: the forward is performed only
    // once every transfer has completed
    this.utilsService.resumeFileUploads(this.uploads);

    this.uploadWatcher = setInterval(() => {
      if (this.uploading()) {
        return;
      }

      this.stopWatchingUploads();
      this.performForward();
    }, 1000);
  }

  // The forward is performed once every transfer has completed: the watch is
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

  private performForward() {
    const endpointUrl = this.tipId ?
      `api/recipient/rtips/${this.tipId}/${this.endpoint}` :
      `api/recipient/rtips/${this.endpoint}`;

    this.http.post(endpointUrl, {
      target_tid: this.selectedTenant,
      answers: this.answers
    }).subscribe({
      next: (response: any) => {
        this.activeModal.close(response);
        if (this.navigateOnSuccess) {
          this.router.navigate(["reports", response.id]).then();
        }
      },
      error: (response: any) => {
        // The modal covers the notification of the errors of the application
        // and the reason of the failure has therefore to be reported here
        this.error = response?.error?.error_message || "Submission failed";
        this.done = false;
      }
    });
  }

  stepForm(index: number): any {
    if (this.stepForms && index !== -1) {
      return this.stepForms.get(index);
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

  onFileUpload(_: any): void {
    this.fieldUtilitiesService.onAnswersUpdate(this);
  }
}
