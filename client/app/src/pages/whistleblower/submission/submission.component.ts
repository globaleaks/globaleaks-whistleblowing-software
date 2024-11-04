import {Component, OnInit, QueryList, ViewChild, ViewChildren} from "@angular/core";
import { ActivatedRoute, Router } from '@angular/router';
import {AppDataService} from "@app/app-data.service";
import {WhistleblowerLoginResolver} from "@app/shared/resolvers/whistleblower-login.resolver";
import {FieldUtilitiesService} from "@app/shared/services/field-utilities.service";
import {SubmissionService} from "@app/services/helper/submission.service";
import {UtilsService} from "@app/shared/services/utils.service";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {NgForm} from "@angular/forms";
import {AppConfigService} from "@app/services/root/app-config.service";
import {Context, Questionnaire, Receiver} from "@app/models/app/public-model";
import {Answers} from "@app/models/reciever/reciever-tip-data";
import {Field} from "@app/models/resolvers/field-template-model";
import * as Flow from "@flowjs/flow.js";
import {TitleService} from "@app/shared/services/title.service";
import {WhistleblowerSubmissionService} from "@app/pages/whistleblower/whistleblower-submission.service";

@Component({
  selector: "src-submission",
  templateUrl: "./submission.component.html",
  providers: [SubmissionService]
})
export class SubmissionComponent implements OnInit {
  @ViewChild("submissionForm") public submissionForm: NgForm;
  @ViewChildren("stepForm") stepForms: QueryList<NgForm>;

  _navigation = -1;
  answers: Answers = {};
  identity_provided = false;
  context_id = "";
  context: Context | undefined = undefined;
  receiversOrderPredicate: string;
  validate: boolean[] = [];
  score = 0;
  done: boolean;
  uploads: { [key: string]: any } = {};
  field_id_map: { [key: string]: Field };
  questionnaire: Questionnaire;
  contextsOrderPredicate: string = this.appDataService.public.node.show_contexts_in_alphabetical_order ? "name" : "order";
  selectable_contexts: Context[];
  show_steps_navigation_bar = false;
  receivedData: Flow[];
  hasNextStepValue: boolean;
  hasPreviousStepValue: boolean;
  areReceiversSelectedValue: boolean;

  constructor(private readonly route:ActivatedRoute, protected whistleblowerSubmissionService:WhistleblowerSubmissionService ,private readonly titleService: TitleService, private readonly router: Router, private readonly appConfigService: AppConfigService, private readonly whistleblowerLoginResolver: WhistleblowerLoginResolver, protected authenticationService: AuthenticationService, private appDataService: AppDataService, private utilsService: UtilsService, private readonly fieldUtilitiesService: FieldUtilitiesService, public submissionService: SubmissionService) {
    this.selectable_contexts = [];
    this.receivedData = this.submissionService.getSharedData();

    this.appConfigService.setPage("submissionpage");
    this.whistleblowerLoginResolver.resolve()
    this.resetForm();
  }

  ngOnInit(): void {
    this.route.queryParamMap.subscribe(params => {
      this.context_id = params.get('context') ?? "";
      this.initializeSubmission();
    });
  }

  firstStepIndex() {
    return this.submissionService.context.allow_recipients_selection ? -1 : 0;
  };

  prepareSubmission(context: any) {
    this.done = false;
    this.answers = {};
    this.uploads = {};
    this.questionnaire = context.questionnaire;

    this.submissionService.create(context.id);
    this.context = context;
    this.fieldUtilitiesService.onAnswersUpdate(this);
    this.utilsService.scrollToTop();

    this.field_id_map = this.fieldUtilitiesService.build_field_id_map(this.questionnaire);
    this.show_steps_navigation_bar = this.context?.allow_recipients_selection ?? this.questionnaire.steps.length > 1;
    this.receiversOrderPredicate = this.submissionService.context.show_receivers_in_alphabetical_order ? "name" : "";

    if (this.context?.allow_recipients_selection) {
      this.navigation = -1;
    } else {
      this.navigation = 0;
    }
  }

  selectable() {
    if (this.submissionService.context.maximum_selectable_receivers === 0) {
      return true;
    }
    return Object.keys(this.submissionService.selected_receivers).length < this.submissionService.context.maximum_selectable_receivers;
  };

  switchSelection(receiver: Receiver) {
    if (receiver.forcefully_selected) {
      return;
    }

    if (this.submissionService.selected_receivers[receiver.id]) {
      delete this.submissionService.selected_receivers[receiver.id];
    } else if (this.selectable()) {
      this.submissionService.selected_receivers[receiver.id] = true;
    }
  };

  selectContext(context: Context) {
    this.context = context;
    this.prepareSubmission(context);
  }

  initializeSubmission() {
    let context = null;

    this.selectable_contexts = this.appDataService.public.contexts.filter(context => !context.hidden);

    if (this.context_id) {
      context = this.appDataService.public.contexts.find(context => context.id === this.context_id);
    } else if (this.selectable_contexts.length === 1) {
      context = this.selectable_contexts[0];
    }

    if (context) {
      this.prepareSubmission(context);
    }
  }

  private updateStatusVariables(): void {
    this.hasPreviousStepValue = this.hasPreviousStep();
    this.hasNextStepValue = this.hasNextStep();
    this.areReceiversSelectedValue = this.areReceiversSelected();
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

  hasPreviousStep() {
    if (typeof this.context === "undefined") {
      return false;
    }

    return this.navigation > this.firstStepIndex();
  };

  areReceiversSelected() {
    return Object.keys(this.submissionService.selected_receivers).length > 0;
  };

  hasNextStep() {
    return this.navigation < this.lastStepIndex();
  }

  lastStepIndex() {
    let last_enabled = 0;
    if (this.questionnaire) {

      for (let i = 0; i < this.questionnaire.steps.length; i++) {
        if (this.fieldUtilitiesService.isFieldTriggered(null, this.questionnaire.steps[i], this.answers, this.score)) {
          last_enabled = i;
        }
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

    if (!isFinite(timeRemaining)) {
      timeRemaining = 0;
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
    if (!isFinite(progress)) {
      progress = 0;
    }
    return progress;
  }

  displaySubmissionErrors() {
    if (!this.validate[this.navigation]) {
      return false;
    }

    this.updateStatusVariables();

    if (!(this.hasPreviousStepValue || !this.hasNextStepValue) && !this.areReceiversSelectedValue) {
      return true;
    }

    return false
  }

  displayErrors() {
    this.updateStatusVariables();

    return this.validate[this.navigation];
  }

  completeSubmission() {
    this.receivedData = this.submissionService.getSharedData();
    if (this.receivedData !== null && this.receivedData !== undefined && this.receivedData.length > 0) {
       this.receivedData.forEach((item :Flow)=> {
        item.upload();
       });
    }

    this.fieldUtilitiesService.onAnswersUpdate(this);

    if (!this.runValidation()) {
      this.utilsService.scrollToTop();
      return;
    }

    this.submissionService.submission.answers = this.answers;

    this.utilsService.resumeFileUploads(this.uploads);
    this.done = true;

    const intervalId = setInterval(() => {
      if (this.uploads) {
        for (const key in this.uploads) {

          if (this.uploads[key].flowFile && this.uploads[key].flowFile.isUploading()) {
            return;
          }
        }
      }
      if (this.uploading()) {
        return;
      }

      this.submissionService.submit().subscribe({
        next: (response) => {
          this.router.navigate(["/"]).then();
          this.authenticationService.session.receipt = response.receipt;
          this.titleService.setPage("receiptpage");
        }
      });

      clearInterval(intervalId);
    }, 1000);
  }

  runValidation() {
    this.validate[this.navigation] = true;
    this.areReceiversSelectedValue = this.areReceiversSelected();

    if (this.submissionService.context.allow_recipients_selection && !this.areReceiversSelectedValue) {
      this.navigation = -1;
    }

    return !(!this.areReceiversSelectedValue || !this.whistleblowerSubmissionService.checkForInvalidFields(this));
  }

  resetForm() {
    if (this.submissionForm) {
      this.submissionForm.reset();
    }
  }

  onFormChange() {
    this.fieldUtilitiesService.onAnswersUpdate(this);
  }

  notifyFileUpload(uploads: any) {
    if (uploads) {
      this.uploads = uploads;
      this.fieldUtilitiesService.onAnswersUpdate(this);
    }
  }
}
