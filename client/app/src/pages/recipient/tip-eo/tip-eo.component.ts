import {ChangeDetectorRef, Component, OnInit, TemplateRef, ViewChild} from "@angular/core";
import {ActivatedRoute, Router} from "@angular/router";
import {AppConfigService} from "@app/services/root/app-config.service";
import {TipService} from "@app/shared/services/tip-service";
import {NgbModal} from "@ng-bootstrap/ng-bootstrap";
import {AppDataService} from "@app/app-data.service";
import {ReceiverTipService} from "@app/services/helper/receiver-tip.service";
import {GrantAccessComponent} from "@app/shared/modals/grant-access/grant-access.component";
import {RevokeAccessComponent} from "@app/shared/modals/revoke-access/revoke-access.component";
import {PreferenceResolver} from "@app/shared/resolvers/preference.resolver";
import {HttpService} from "@app/shared/services/http.service";
import {UtilsService} from "@app/shared/services/utils.service";
import {Observable} from "rxjs";
import {
  TipOperationSetReminderComponent
} from "@app/shared/modals/tip-operation-set-reminder/tip-operation-set-reminder.component";
import {DeleteConfirmationComponent} from "@app/shared/modals/delete-confirmation/delete-confirmation.component";
import {HttpClient} from "@angular/common/http";
import {
  TipOperationPostponeComponent
} from "@app/shared/modals/tip-operation-postpone/tip-operation-postpone.component";
import {TransferAccessComponent} from "@app/shared/modals/transfer-access/transfer-access.component";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {Tab} from "@app/models/component-model/tab";
import {RecieverTipData, Children3} from "@app/models/reciever/reciever-tip-data";
import {Receiver} from "@app/models/app/public-model";
import {TipUploadWbFileComponent} from "@app/shared/partials/tip-upload-wbfile/tip-upload-wb-file.component";
import {TipCommentsComponent} from "@app/shared/partials/tip-comments/tip-comments.component";
import {ReopenSubmissionComponent} from "@app/shared/modals/reopen-submission/reopen-submission.component";
import {ChangeSubmissionStatusComponent} from "@app/shared/modals/change-submission-status/change-submission-status.component";
import {TranslateService} from "@ngx-translate/core";

@Component({
  selector: "src-tip-eo",
  templateUrl: "./tip-eo.component.html",
})
export class TipEoComponent implements OnInit {
  @ViewChild("tab1") tab1!: TemplateRef<TipUploadWbFileComponent | TipCommentsComponent>;
  @ViewChild("tab2") tab2!: TemplateRef<TipUploadWbFileComponent | TipCommentsComponent>;
  @ViewChild("tab3") tab3!: TemplateRef<TipUploadWbFileComponent | TipCommentsComponent>;
  @ViewChild("tab4") tab4!: TemplateRef<TipUploadWbFileComponent | TipCommentsComponent>;

  tip_id: string | null;
  tip: any;
  score: number;
  ctx: string;
  showEditLabelInput: boolean;
  tabs: Tab[];
  active: string;
  loading = true;
  redactMode :boolean = false;
  redactOperationTitle: string;
  questionnaireData: {
    textareaAnswer: string;
    reviewFormFields: Children3[];
  } = {
    textareaAnswer: '',
    reviewFormFields: []
  };

  uploads: { [key: string]: any } = {};

  answers: any

  done: boolean = false;

  constructor(private readonly translateService: TranslateService,private readonly tipService: TipService, private readonly appConfigServices: AppConfigService, private readonly router: Router, private readonly cdr: ChangeDetectorRef, protected utils: UtilsService, protected preferencesService: PreferenceResolver, protected modalService: NgbModal, private readonly activatedRoute: ActivatedRoute, protected httpService: HttpService, protected http: HttpClient, protected appDataService: AppDataService, protected RTipService: ReceiverTipService, private utilsService: UtilsService, protected authenticationService: AuthenticationService) {
  }

  ngOnInit() {
    this.loadTipDate();
    this.cdr.detectChanges();
  }

  loadTipDate() {
    this.tip_id = this.activatedRoute.snapshot.paramMap.get("tip_id");
    this.redactOperationTitle = this.translateService.instant('Mask') + ' / ' + this.translateService.instant('Redact');
    const requestObservable: Observable<any> = this.httpService.receiverTip(this.tip_id);
    this.loading = true;
    this.RTipService.reset();
    requestObservable.subscribe(
      {
        next: (response: RecieverTipData) => {
          this.loading = false;
          this.RTipService.initialize(response);
          this.tip = this.RTipService.tip;
          this.activatedRoute.queryParams.subscribe((params: { [x: string]: string; }) => {
            this.tip.tip_id = params["tip_id"];
          });

          this.tip.receivers_by_id = this.utils.array_to_map(this.tip.receivers);
          this.score = this.tip.score;
          this.ctx = "rtip";
          this.showEditLabelInput = this.tip.label === "";
          
          this.preprocessTipAnswers(this.tip);
          this.tip.submissionStatusStr = this.utils.getSubmissionStatusText(this.tip.status, this.tip.substatus, this.appDataService.submissionStatuses);
          this.initNavBar()
          this.populateQuestionnaireData()
        }
      }
    );
  }

  populateQuestionnaireData() {
    const answerId = this.tip.questionnaires[0].steps[0].children

    if (typeof this.tip.questionnaires[0].answers  === 'string' || this.tip.questionnaires[0].answers instanceof String)
      this.answers = JSON.parse(this.tip.questionnaires[0].answers)
    else
      this.answers = this.tip.questionnaires[0].answers 

    this.questionnaireData.textareaAnswer = this.answers[answerId[0].id][0].value;
    this.questionnaireData.reviewFormFields = this.tip.questionnaires[0].steps[1].children 

  }

  initNavBar() {
    setTimeout(() => {
      this.active = "Whistleblower";
      this.tabs = [
        {
          title: "Whistleblower",
          component: this.tab1
        },
        {
          title: "Primary Organization",
          component: this.tab2
        }
      ];

      if(this.preferencesService.dataModel.t_affiliated) {
        
        this.tabs = [...this.tabs, ...[{
          title: "Internal",
          component: this.tab3
        },
        {
          title: "Only me",
          component: this.tab4
        }]];
      }
    });

  }


  openGrantTipAccessModal() {
    this.utils.runUserOperation("get_users_names", {}, false).subscribe({
      next: response => {
        const selectableRecipients: Receiver[] = [];
        this.appDataService.public.receivers.forEach(async (receiver: Receiver) => {
          if (receiver.id !== this.authenticationService.session.user_id && !this.tip.receivers_by_id[receiver.id]) {
            selectableRecipients.push(receiver);
          }
        });
        const modalRef = this.modalService.open(GrantAccessComponent, {backdrop: 'static', keyboard: false});
        modalRef.componentInstance.usersNames = response;
        modalRef.componentInstance.selectableRecipients = selectableRecipients;
        modalRef.componentInstance.confirmFun = (receiver_id: Receiver) => {
          const req = {
            operation: "grant",
            args: {
              receiver: receiver_id.id
            },
          };
          this.httpService.tipOperation(req.operation, req.args, this.RTipService.tip.id)
            .subscribe(() => {
              this.reload();
            });
        };
        modalRef.componentInstance.cancelFun = null;
      }
    });
  }

  openRevokeTipAccessModal() {
    this.utils.runUserOperation("get_users_names", {}, false).subscribe(
      {
        next: response => {
          const selectableRecipients: Receiver[] = [];
          this.appDataService.public.receivers.forEach(async (receiver: Receiver) => {
            if (receiver.id !== this.authenticationService.session.user_id && this.tip.receivers_by_id[receiver.id]) {
              selectableRecipients.push(receiver);
            }
          });
          const modalRef = this.modalService.open(RevokeAccessComponent, {backdrop: 'static', keyboard: false});
          modalRef.componentInstance.usersNames = response;
          modalRef.componentInstance.selectableRecipients = selectableRecipients;
          modalRef.componentInstance.confirmFun = (receiver_id: Receiver) => {
            const req = {
              operation: "revoke",
              args: {
                receiver: receiver_id.id
              },
            };
            this.httpService.tipOperation(req.operation, req.args, this.RTipService.tip.id)
              .subscribe(() => {
                this.reload();
              });
          };
          modalRef.componentInstance.cancelFun = null;
        }
      }
    );
  }

  openTipTransferModal() {
    this.utils.runUserOperation("get_users_names", {}, false).subscribe(
      {
        next: response => {
          const selectableRecipients: Receiver[] = [];
          this.appDataService.public.receivers.forEach(async (receiver: Receiver) => {
            if (receiver.id !== this.authenticationService.session.user_id && !this.tip.receivers_by_id[receiver.id]) {
              selectableRecipients.push(receiver);
            }
          });
          const modalRef = this.modalService.open(TransferAccessComponent, {backdrop: 'static', keyboard: false});
          modalRef.componentInstance.usersNames = response;
          modalRef.componentInstance.selectableRecipients = selectableRecipients;
          modalRef.result.then(
            (receiverId) => {
              if (receiverId) {
                const req = {
                  operation: "transfer",
                  args: {
                    receiver: receiverId,
                  },
                };
                this.http
                  .put(`api/recipient/rtips/${this.tip.id}`, req)
                  .subscribe(() => {
                    this.router.navigate(["recipient", "reports"]).then();
                  });
              }
            },
            () => {
            }
          );
        }
      }
    );
  }

  openModalChangeState(){
    const modalRef = this.modalService.open(ChangeSubmissionStatusComponent, {backdrop: 'static', keyboard: false});
    modalRef.componentInstance.arg={
      tip:this.tip,
      motivation:this.tip.motivation,
      submission_statuses:this.prepareSubmissionStatuses(),
    };

    modalRef.componentInstance.confirmFunction = (status:any,motivation: string) => {
      this.tip.status = status.status;
      this.tip.substatus = status.substatus;
      this.tip.motivation = motivation;
      this.updateSubmissionStatus();
    };
    modalRef.componentInstance.cancelFun = null;
  }

  openModalReopen(){
    const modalRef = this.modalService.open(ReopenSubmissionComponent, {backdrop: 'static', keyboard: false});
    modalRef.componentInstance.confirmFunction = (motivation: string) => {
      this.tip.status = "opened";
      this.tip.substatus = "";
      this.tip.motivation = motivation;
      this.updateSubmissionStatus();
    };
    modalRef.componentInstance.cancelFun = null;
  }

  updateSubmissionStatus() {
    const args = {"status":  this.tip.status, "substatus": this.tip.substatus ? this.tip.substatus : "", "motivation":  this.tip.motivation || ""};
    this.httpService.tipOperation("update_status", args, this.tip.id)
      .subscribe(
        () => {
          this.utils.reloadComponent();
        }
      );
  };

  prepareSubmissionStatuses() {
    const subCopy:any[]= [...this.appDataService.submissionStatuses];
    const output = [];
    for (const x of subCopy) {
      if (x.substatuses.length) {
        for (const y of x.substatuses) {
          output.push({
            id: `${x.id}:${y.id}`,
            label: this.translateService.instant(x.label) + ' \u2013 ' + y.label,
            status: x.id,
            substatus: y.id,
            order: output.length,
          });
        }
      } else {
        x.status = x.id;
        x.substatus = "";
        x.order = output.length;
        output.push(x);
      }
    }
    return output;
  }

  reload(): void {
    const reloadCallback = () => {
      this.utils.reloadComponent();
    };

    this.appConfigServices.localInitialization(true, reloadCallback);
  }

  preprocessTipAnswers(tip: any) {
    if (typeof tip.questionnaires[0].answers  === 'string' || tip.questionnaires[0].answers instanceof String)
      tip.questionnaires[0].answers = JSON.parse(tip.questionnaires[0].answers)
    
    this.tipService.preprocessTipAnswers(tip);
  }

  tipToggleStar() {
    this.httpService.tipOperation("set", {
      "key": "important",
      "value": !this.RTipService.tip.important
    }, this.RTipService.tip.id)
      .subscribe(() => {
        this.RTipService.tip.important = !this.RTipService.tip.important;
      });
  }

  tipNotify(enable: boolean) {
    this.httpService.tipOperation("set", {"key": "enable_notifications", "value": enable}, this.RTipService.tip.id)
      .subscribe(() => {
        this.RTipService.tip.enable_notifications = enable;
      });
  }

  tipDelete() {
    const modalRef = this.modalService.open(DeleteConfirmationComponent, {backdrop: 'static', keyboard: false});
    modalRef.componentInstance.confirmFunction = () => {
    };
    modalRef.componentInstance.args = {
      tip: this.RTipService.tip,
      operation: "delete"
    };
  }

  setReminder() {
    const modalRef = this.modalService.open(TipOperationSetReminderComponent, {backdrop: 'static', keyboard: false});
    modalRef.componentInstance.args = {
      tip: this.RTipService.tip,
      operation: "set_reminder",
      contexts_by_id: this.appDataService.contexts_by_id,
      reminder_date: this.utils.getPostponeDate(this.appDataService.contexts_by_id[this.tip.context_id].tip_reminder),
      dateOptions: {
        minDate: new Date(this.tip.creation_date)
      },
      opened: false,

    };
  }

  tipPostpone() {
    const modalRef = this.modalService.open(TipOperationPostponeComponent, {backdrop: 'static', keyboard: false});
    modalRef.componentInstance.args = {
      tip: this.RTipService.tip,
      operation: "postpone",
      contexts_by_id: this.appDataService.contexts_by_id,
      expiration_date: this.utils.getPostponeDate(this.appDataService.contexts_by_id[this.tip.context_id].tip_timetolive),
      dateOptions: {
        minDate: new Date(this.tip.expiration_date),
        maxDate: this.utils.getPostponeDate(Math.max(365, this.appDataService.contexts_by_id[this.tip.context_id].tip_timetolive * 2))
      },
      opened: false,
      Utils: this.utils
    };
  }


  listenToFields() {
    this.loadTipDate();
  }

  protected readonly JSON = JSON;

  closeForwardedReport(){

    this.loading = true;

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

     this.httpService.requestForwardedReportClosing(this.RTipService.tip.id, JSON.stringify(this.answers)).subscribe({
      next: (response) => {
        this.loading = false;
        this.RTipService.tip.status = 'closed';
        this.loadTipDate();
      }
    });

      clearInterval(intervalId);
    }, 1000);

    
          
  }

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

  notifyFileUpload(uploads: any) {
    if (uploads) {
      this.uploads = {...this.uploads, ...uploads};
    }
  }



}
