import {NgClass} from "@angular/common";
import {Component, Input, OnInit, QueryList, ViewChild, ViewChildren, inject} from "@angular/core";
import {FormsModule, NgForm} from "@angular/forms";
import {Router} from "@angular/router";
import {Answers, Questionnaire} from "@app/models/receiver/receiver-tip-data";
import {WhistleblowerSubmissionService} from "@app/pages/whistleblower/whistleblower-submission.service";
import {FormComponent} from "@app/pages/whistleblower/form/form.component";
import {NgFormChangeDirective} from "@app/shared/directive/ng-form-change.directive";
import {OrderByPipe} from "@app/shared/pipes/order-by.pipe";
import {TranslatorPipe} from "@app/shared/pipes/translate";
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
  imports: [FormsModule, NgClass, NgFormChangeDirective, FormComponent, TranslateModule, TranslatorPipe, OrderByPipe]
})
export class ForwardReportComponent implements OnInit {
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
  file_upload_url = "";

  ngOnInit(): void {
    this.selectedTenant = this.tenants.length ? this.tenants[0].id : null;
    this.fieldUtilitiesService.onAnswersUpdate(this);
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

  completeSubmission() {
    this.fieldUtilitiesService.onAnswersUpdate(this);
    if (!this.runValidation() || this.selectedTenant === null) {
      return;
    }

    const endpointUrl = this.tipId ?
      `api/recipient/rtips/${this.tipId}/${this.endpoint}` :
      `api/recipient/rtips/${this.endpoint}`;

    this.done = true;
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
      error: () => {
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

  onFileUpload(_: any): void {}
}
