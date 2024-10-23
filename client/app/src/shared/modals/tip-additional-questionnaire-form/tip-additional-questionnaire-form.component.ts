import {Component, OnInit, QueryList, ViewChild, ViewChildren, inject} from "@angular/core";
import {WbTipResolver} from "@app/shared/resolvers/wb-tip-resolver.service";
import {NgbActiveModal} from "@ng-bootstrap/ng-bootstrap";
import {NgForm, FormsModule} from "@angular/forms";
import {WbtipService} from "@app/services/helper/wbtip.service";
import {FieldUtilitiesService} from "@app/shared/services/field-utilities.service";
import {UtilsService} from "@app/shared/services/utils.service";
import {HttpService} from "@app/shared/services/http.service";
import {Answers, Questionnaire3} from "@app/models/receiver/receiver-tip-data";
import {Field} from "@app/models/resolvers/field-template-model";
import {WhistleblowerSubmissionService} from "@app/pages/whistleblower/whistleblower-submission.service";
import {NgClass} from "@angular/common";
import {NgFormChangeDirective} from "../../directive/ng-form-change.directive";
import {StepErrorComponent} from "@app/pages/whistleblower/step-error/step-error.component";
import {FormComponent} from "@app/pages/whistleblower/form/form.component";
import {RFilesUploadStatusComponent} from "../../partials/rfiles-upload-status/r-files-upload-status.component";
import {TranslateModule} from "@ngx-translate/core";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {OrderByPipe} from "@app/shared/pipes/order-by.pipe";

@Component({
    selector: "src-tip-additional-questionnaire-form",
    templateUrl: "./tip-additional-questionnaire-form.component.html",
    standalone: true,
    imports: [FormsModule, NgClass, NgFormChangeDirective, StepErrorComponent, FormComponent, RFilesUploadStatusComponent, TranslateModule, TranslatorPipe, OrderByPipe]
})
export class TipAdditionalQuestionnaireFormComponent implements OnInit {
  protected whistleblowerSubmissionService = inject(WhistleblowerSubmissionService);
  private wbTipResolver = inject(WbTipResolver);
  private httpService = inject(HttpService);
  private fieldUtilitiesService = inject(FieldUtilitiesService);
  private utilsService = inject(UtilsService);
  protected wbTipService = inject(WbtipService);
  protected activeModal = inject(NgbActiveModal);

  @ViewChild("submissionForm") public submissionForm: NgForm;
  @ViewChildren("stepForm") stepForms: QueryList<NgForm>;

  _navigation: number = 0;
  validate: boolean[] = [];
  score: number = 0;
  questionnaire: Questionnaire3;
  answers: Answers = {};
  field_id_map: { [key: string]: Field };
  done: boolean = false;
  uploads: { [key: string]: any };
  file_upload_url: string = "api/whistleblower/wbtip/wbfiles";
  hasPreviousStepValue: boolean;
  hasNextStepValue: boolean;

  ngOnInit(): void {
    this.prepareSubmission();
  }

  private updateStatusVariables(): void {
    this.hasPreviousStepValue = this.hasPreviousStep();
    this.hasNextStepValue = this.hasNextStep();
  }

  get navigation(): any {
    return this._navigation;
  }

  set navigation(value: any) {
    if (this._navigation !== value) {
      this._navigation = value;
      this.handleNavigationChange();
    }
  }

  private handleNavigationChange(): void {
    this.updateStatusVariables();
  }

  goToStep(step: number) {
    this.navigation = step;
    this.utilsService.scrollToTop();
  }

  firstStepIndex() {
    return 0;
  };

  lastStepIndex() {
    let last_enabled = 0;

    for (let i = 0; i < this.questionnaire.steps.length; i++) {
      if (this.questionnaire.steps[i].enabled) {
        last_enabled = i;
      }
    }

    return last_enabled;
  };

  uploading() {
    let uploading = false;
    if (this.uploads && this.done) {
      for (const key in this.uploads) {
        if (this.uploads[key].flowJs && this.uploads[key].flowJs.isUploading()) {
          uploading = true;
        }
      }
    }

    return uploading;
  }

  calculateEstimatedTime() {
    let timeRemaining = 0;
    if (this.uploads && this.done) {
      for (const key in this.uploads) {
        if (this.uploads[key] && this.uploads[key].flowJs) {
          timeRemaining += this.uploads[key].flowJs.timeRemaining();
        }
      }
    }

    return timeRemaining;
  }

  calculateProgress() {
    let progress = 0;
    if (this.uploads && this.done) {
      for (const key in this.uploads) {
        if (this.uploads[key] && this.uploads[key].flowJs) {
          progress += this.uploads[key].flowJs.progress();
        }
      }
    }

    return progress;
  }

  hasNextStep() {
    return this.navigation < this.lastStepIndex();
  };

  hasPreviousStep() {
    return this.navigation > this.firstStepIndex();
  };

  runValidation() {
    this.validate[this.navigation] = true;

    if (!this.whistleblowerSubmissionService.checkForInvalidFields(this)) {
      this.utilsService.scrollToTop();
      return false;
    }

    return true;
  };

  areReceiversSelected() {
    return true;
  };

  prepareSubmission() {
    this.done = false;
    this.answers = {};
    this.uploads = {};
    this.questionnaire = this.wbTipService.tip.additional_questionnaire;
    this.fieldUtilitiesService.onAnswersUpdate(this);
    this.field_id_map = this.fieldUtilitiesService.build_field_id_map(this.questionnaire);
  };

  completeSubmission() {
    this.fieldUtilitiesService.onAnswersUpdate(this);

    if (!this.runValidation()) {
      this.utilsService.scrollToTop();
      return;
    }

    this.done = true;
    this.utilsService.resumeFileUploads(this.uploads);

    const intervalId = setInterval(() => {
      if (this.uploads) {
        for (const key in this.uploads) {
          if (this.uploads[key].flowFile && this.uploads[key].flowFile.isUploading()) {
            return;
          }
        }
      }
      this.fieldUtilitiesService.onAnswersUpdate(this);

      if (this.uploading()) {
        return;
      }

      this.httpService.whistleBlowerTipUpdate({
        "cmd": "additional_questionnaire",
        "answers": this.answers
      }).subscribe
      (
        {
          next: _ => {
            this.wbTipResolver.onReload(() => {
              this.utilsService.reloadCurrentRoute();
            });
          }
        }
      );

      clearInterval(intervalId);
      this.activeModal.dismiss();
    }, 1000);
  }

  stepForm(index: number): any {
    if (this.stepForms && index !== -1) {
      return this.stepForms.get(index);
    }
  };

  displayStepErrors(index: number): any {
    if (index !== -1) {
      const response = this.stepForm(index);
      if (response) {
        return response?.invalid;
      } else {
        return false;
      }
    }
  };

  displayErrors() {
    this.updateStatusVariables();

    if (!(this.validate[this.navigation])) {
      return false;
    }

    return !!this.displayStepErrors(this.navigation);
  };

  onFormChange() {
    this.fieldUtilitiesService.onAnswersUpdate(this);
  }

  onFileUpload(upload: any) {
    if (upload) {
      this.uploads = upload;
      this.fieldUtilitiesService.onAnswersUpdate(this);
    }
  }
}
