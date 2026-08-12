import {Component, ViewChild, inject} from "@angular/core";
import {SubmissionStatus} from "@app/models/app/shared-public-model";
import {Answers, RecieverTipData} from "@app/models/receiver/receiver-tip-data";
import {NgbActiveModal, NgbModal} from "@ng-bootstrap/ng-bootstrap";
import {FormsModule, NgForm} from "@angular/forms";

import {TranslateModule} from "@ngx-translate/core";
import {OrderByPipe} from "@app/shared/pipes/order-by.pipe";
import {FormComponent} from "@app/pages/whistleblower/form/form.component";
import {NgFormChangeDirective} from "@app/shared/directive/ng-form-change.directive";
import {FieldUtilitiesService} from "@app/shared/services/field-utilities.service";
@Component({
    selector: 'src-change-submission-status',
    templateUrl: './change-submission-status.component.html',
    standalone: true,
    imports: [
    FormComponent,
    FormsModule,
    NgFormChangeDirective,
    OrderByPipe,
    TranslateModule
],
})
export class ChangeSubmissionStatusComponent {
  private modalService = inject(NgbModal);
  private activeModal = inject(NgbActiveModal);
  private fieldUtilitiesService = inject(FieldUtilitiesService);

  arg: {tip:RecieverTipData, submission_statuses:SubmissionStatus[],status:any, closure_questionnaire:any};

  confirmFunction: (status:SubmissionStatus, answers?:Answers) => void;

  questionnaire: any = null;
  answers: Answers = {};
  uploads: Record<string, any> = {};

  @ViewChild('closureForm') closureForm?: NgForm;

    closureQuestionnaireRequired() {
      return !!(this.arg.closure_questionnaire && this.arg.status && this.arg.status.status === 'closed');
    }

    // The steps of the questionnaire carry their enabled flag only once the
    // answers are evaluated, exactly as during a submission
    onStatusChange() {
      if (this.closureQuestionnaireRequired()) {
        this.questionnaire = this.arg.closure_questionnaire;
        this.onFormChange();
      }
    }

    onFormChange() {
      this.fieldUtilitiesService.onAnswersUpdate(this);
    }

    confirmDisabled() {
      return this.closureQuestionnaireRequired() && !!this.closureForm?.invalid;
    }

    confirm(status: SubmissionStatus) {
      if(status){
        this.confirmFunction(status, this.closureQuestionnaireRequired() ? this.answers : undefined);
        return this.activeModal.close(status);
      }else{
        this.cancel()
      }
    }

    cancel() {
      this.modalService.dismissAll();
    }
}
