import {ChangeDetectorRef, Component, OnInit, TemplateRef, ViewChild, inject} from "@angular/core";
import {FormsModule} from "@angular/forms";
import {ActivatedRoute, Router, RouterLink} from "@angular/router";
import {AppConfigService} from "@app/services/root/app-config.service";
import {TipService} from "@app/shared/services/tip-service";
import {NgbModal, NgbNav, NgbNavItem, NgbNavItemRole, NgbNavLinkButton, NgbNavLinkBase, NgbNavContent, NgbNavOutlet, NgbTooltipModule, NgbDropdown, NgbDropdownToggle, NgbDropdownMenu} from "@ng-bootstrap/ng-bootstrap";
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
import {CryptoService} from "@app/shared/services/crypto.service";
import {TransferAccessComponent} from "@app/shared/modals/transfer-access/transfer-access.component";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {Tab} from "@app/models/component-model/tab";
import {RecieverTipData} from "@app/models/receiver/receiver-tip-data";
import {Receiver} from "@app/models/app/public-model";
import {TipUploadWbFileComponent} from "@app/shared/partials/tip-upload-wbfile/tip-upload-wb-file.component";
import {TipCommentsComponent} from "@app/shared/partials/tip-comments/tip-comments.component";
import {ReopenSubmissionComponent} from "@app/shared/modals/reopen-submission/reopen-submission.component";
import {ChangeSubmissionStatusComponent} from "@app/shared/modals/change-submission-status/change-submission-status.component";
import {TranslateService, TranslateModule} from "@ngx-translate/core";
import {DatePipe, NgClass, NgTemplateOutlet} from "@angular/common";
import {TipInfoComponent} from "@app/shared/partials/tip-info/tip-info.component";
import {TipReceiverListComponent} from "@app/shared/partials/tip-receiver-list/tip-receiver-list.component";
import {TipQuestionnaireAnswersComponent} from "@app/shared/partials/tip-questionnaire-answers/tip-questionnaire-answers.component";
import {WhistleBlowerIdentityReceiverComponent} from "../whistleblower-identity-receiver/whistleblower-identity-receiver.component";
import {TipFilesReceiverComponent} from "@app/shared/partials/tip-files-receiver/tip-files-receiver.component";
import {TipUploadWbFileComponent as TipUploadWbFileComponent_1} from "../../../shared/partials/tip-upload-wbfile/tip-upload-wb-file.component";
import {TipCommentsComponent as TipCommentsComponent_1} from "../../../shared/partials/tip-comments/tip-comments.component";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {TipAuditLogComponent} from "@app/shared/modals/tip-audit-log/tip-audit-log.component";
import {ForwardReportComponent} from "@app/shared/modals/forward-report/forward-report.component";
import {ConfirmationComponent} from "@app/shared/modals/confirmation/confirmation.component";


@Component({
    selector: "src-tip",
    templateUrl: "./tip.component.html",
    standalone: true,
    imports: [
      FormsModule,
      NgClass,
      DatePipe,
      RouterLink,
      TipInfoComponent,
      TipReceiverListComponent,
      TipQuestionnaireAnswersComponent,
      WhistleBlowerIdentityReceiverComponent,
      TipFilesReceiverComponent,
      NgbNav,
      NgbNavItem,
      NgbNavItemRole,
      NgbNavLinkButton,
      NgbNavLinkBase,
      NgbNavContent,
      NgTemplateOutlet,
      NgbNavOutlet,
      NgbTooltipModule,
      NgbDropdown,
      NgbDropdownToggle,
      NgbDropdownMenu,
      TipUploadWbFileComponent_1,
      TipCommentsComponent_1,
      TranslateModule,
      TranslatorPipe
    ]
})
export class TipComponent implements OnInit {
  private translateService = inject(TranslateService);
  private tipService = inject(TipService);
  private appConfigServices = inject(AppConfigService);
  private router = inject(Router);
  private cdr = inject(ChangeDetectorRef);
  private cryptoService = inject(CryptoService);
  protected utils = inject(UtilsService);
  protected preferencesService = inject(PreferenceResolver);
  protected modalService = inject(NgbModal);
  private activatedRoute = inject(ActivatedRoute);
  protected httpService = inject(HttpService);
  protected http = inject(HttpClient);
  protected appDataService = inject(AppDataService);
  protected RTipService = inject(ReceiverTipService);
  protected authenticationService = inject(AuthenticationService);

  @ViewChild("tab1") tab1!: TemplateRef<TipUploadWbFileComponent | TipCommentsComponent>;
  @ViewChild("tab2") tab2!: TemplateRef<TipUploadWbFileComponent | TipCommentsComponent>;
  @ViewChild("tab3") tab3!: TemplateRef<TipUploadWbFileComponent | TipCommentsComponent>;

  tip_id: string | null;
  tip: RecieverTipData;
  score: number;
  ctx: string;
  showEditLabelInput: boolean;
  active: string;
  loading = true;
  redactMode:boolean = false;
  redactOperationTitle: string;
  tabs: Tab[];
  submission: any;

  ngOnInit() {
    this.activatedRoute.paramMap.subscribe(params => {
      const tipId = params.get("tip_id");
      if (tipId && tipId !== this.tip_id) {
        this.loadTipData(tipId);
      }
    });
  }

  loadTipData(tipId: string | null = this.activatedRoute.snapshot.paramMap.get("tip_id")) {
    this.tip_id = tipId;
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
          this.submission = { submission: this.tip, identity_provided: this.tip.identity_provided };

          this.tip.tip_id = this.activatedRoute.snapshot.queryParamMap.get("tip_id") || "";

          this.tip.receivers_by_id = this.utils.array_to_map(this.tip.receivers);
          this.score = this.tip.score;
          this.ctx = "rtip";
          this.showEditLabelInput = this.tip.label === "";
          this.preprocessTipAnswers(this.tip);
          this.tip.submissionStatusStr = this.utils.getSubmissionStatusText(this.tip.status, this.tip.substatus, this.appDataService.submissionStatuses);
          setTimeout(() => {
              this.initNavBar();
          });
          this.cdr.markForCheck();
        }
      }
    );
  }

  initNavBar() {
    setTimeout(() => {
      this.active = this.active || "Everyone";
      this.tabs = [
        {
          title: "Everyone",
          component: this.tab1
        },
        {
          title: "Recipients only",
          component: this.tab2
        },
        {
          title: "Me only",
          component: this.tab3
        },
      ];
    });
  }

  isForwardManagedReport() {
    return this.tip?.type === "forward-request" || this.tip?.type === "forward";
  }

  isForwardFromRootTenant() {
    return Number(this.tip?.data?.forwarded_from?.source_tid) === 1;
  }

  canEditExpiration() {
    if (!this.tip?.context || !this.preferencesService.dataModel.profile.permissions.can_postpone_expiration) {
      return false;
    }

    if (!this.isForwardManagedReport()) {
      return true;
    }

    if (this.preferencesService.dataModel.tid !== 1) {
      return false;
    }

    return this.tip.type !== "forward" || !this.isForwardFromRootTenant();
  }

  canDeleteReport() {
    if (!this.preferencesService.dataModel.profile.permissions.can_delete_submission) {
      return false;
    }

    return !this.isForwardManagedReport() || this.preferencesService.dataModel.tid === 1;
  }

  updateLabel(label: string) {
    this.httpService.tipOperation("set", {"key": "label", "value": label}, this.RTipService.tip.id).subscribe(() => {
    });
  }

  openGrantTipAccessModal(): void {
    this.utils.runUserOperation("get_users_names", {}, false).subscribe({
      next: response => {
        const names = response as Record<string, string>;
        const selectableRecipients: Receiver[] = [];
        this.appDataService.public.receivers.forEach(async (receiver: Receiver) => {
          if (receiver.id !== this.authenticationService.session.user_id && !this.tip.receivers_by_id[receiver.id]) {
            receiver.name = names[receiver.id];
            selectableRecipients.push(receiver);
          }
        });
        const modalRef = this.modalService.open(GrantAccessComponent, {backdrop: 'static', keyboard: false});
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
          const names = response as Record<string, string>;
          const selectableRecipients: Receiver[] = [];
          this.appDataService.public.receivers.forEach(async (receiver: Receiver) => {
            if (receiver.id !== this.authenticationService.session.user_id && this.tip.receivers_by_id[receiver.id]) {
              receiver.name = names[receiver.id];
              selectableRecipients.push(receiver);
            }
          });
          const modalRef = this.modalService.open(RevokeAccessComponent, {backdrop: 'static', keyboard: false});
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
          const names = response as Record<string, string>;
          const selectableRecipients: Receiver[] = [];
          this.appDataService.public.receivers.forEach(async (receiver: Receiver) => {
            if (receiver.id !== this.authenticationService.session.user_id && !this.tip.receivers_by_id[receiver.id]) {
              receiver.name = names[receiver.id];
              selectableRecipients.push(receiver);
            }
          });
          const modalRef = this.modalService.open(TransferAccessComponent, {backdrop: 'static', keyboard: false});
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

  openForwardModal() {
    this.http.get(`api/recipient/rtips/${this.tip.id}/forward`).subscribe((response: any) => {
      const modalRef = this.modalService.open(ForwardReportComponent, {
        size: 'xl',
        backdrop: 'static',
        keyboard: false
      });
      modalRef.componentInstance.tipId = this.tip.id;
      modalRef.componentInstance.tenants = response.tenants;
      modalRef.componentInstance.questionnaire = response.questionnaire;
      modalRef.result.then(
        () => this.reload(),
        () => {}
      );
    });
  }

  authorizeForward() {
    const modalRef = this.modalService.open(ConfirmationComponent, {
      backdrop: 'static',
      keyboard: false,
      ariaLabelledBy: 'modal-title'
    });
    modalRef.componentInstance.title = "Authorize forward";
    modalRef.componentInstance.message = "By confirming, this forward request will become a normal report.";
    modalRef.componentInstance.confirmLabel = "Authorize";
    modalRef.componentInstance.confirmFunction = () => {
      const req = {
        operation: "set",
        args: {
          key: "allow_forward",
          value: true
        }
      };

      this.http.put(`api/recipient/rtips/${this.tip.id}`, req).subscribe(() => {
        this.reload();
      });
    };
  }

  openModalChangeState(){
    const modalRef = this.modalService.open(ChangeSubmissionStatusComponent, {backdrop: 'static', keyboard: false});
    modalRef.componentInstance.arg={
      tip:this.tip,
      submission_statuses:this.prepareSubmissionStatuses(),
    };

    modalRef.componentInstance.confirmFunction = (status:any) => {
      this.tip.status = status.status;
      this.tip.substatus = status.substatus;
      this.updateSubmissionStatus();
    };
    modalRef.componentInstance.cancelFun = null;
  }

  openModalReopen(){
    const modalRef = this.modalService.open(ReopenSubmissionComponent, {backdrop: 'static', keyboard: false});
    modalRef.componentInstance.confirmFunction = () => {
      this.tip.status = "opened";
      this.tip.substatus = "";
      this.updateSubmissionStatus();
    };
    modalRef.componentInstance.cancelFun = null;
  }

  updateSubmissionStatus() {
    const args = {"status":  this.tip.status, "substatus": this.tip.substatus ? this.tip.substatus : ""};
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
            label: (x.label ? this.translateService.instant(x.label) : '') + ' \u2013 ' + y.label,
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
    this.utils.reloadComponent();
  }

  preprocessTipAnswers(tip: RecieverTipData) {
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
    const tip_reminder = this.appDataService.contexts_by_id?.[this.tip.context_id]?.tip_reminder ?? 0;
    const modalRef = this.modalService.open(TipOperationSetReminderComponent, {backdrop: 'static', keyboard: false});
    modalRef.componentInstance.args = {
      tip: this.RTipService.tip,
      operation: "set_reminder",
      reminder_date: this.utils.getPostponeDate(tip_reminder),
      dateOptions: {
        minDate: new Date(this.tip.creation_date)
      },
      opened: false,
    };
  }

  tipPostpone() {
    const tip_timetolive = this.appDataService.contexts_by_id?.[this.tip.context_id]?.tip_timetolive ?? 90;
    const modalRef = this.modalService.open(TipOperationPostponeComponent, {backdrop: 'static', keyboard: false});
    modalRef.componentInstance.args = {
      tip: this.RTipService.tip,
      operation: "postpone",
      expiration_date: this.utils.getPostponeDate(tip_timetolive),
      dateOptions: {
        minDate: this.utils.getMinPostponeDate(this.tip.expiration_date),
        maxDate: this.utils.getPostponeDate(Math.max(365, tip_timetolive * 2))
      },
      opened: false,
      Utils: this.utils
    };
  }

  exportTip(tipId: string) {
    this.utils.saveAs(this.authenticationService, "tip.zip", `/api/recipient/tips/${tipId}/export`);
  }

  openLogsModal() {
    const modalRef = this.modalService.open(TipAuditLogComponent, {
      size: 'xl',
      backdrop: 'static',
      keyboard: false
    });

    modalRef.componentInstance.tipId = this.tip_id;
    modalRef.componentInstance.tipData = this.tip; // Pass the tip data containing comments with audit logs
    modalRef.componentInstance.usersData = this.tip?.receivers || []; // Pass receivers as users data
  }

  toggleRedactMode() {
    this.redactMode = !this.redactMode;
  }

  listenToFields() {
    this.loadTipData();
  }

  protected readonly JSON = JSON;
}
