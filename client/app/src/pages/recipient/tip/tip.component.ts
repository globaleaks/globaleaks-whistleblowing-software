import {ChangeDetectorRef, Component, OnInit, inject} from "@angular/core";
import {FormsModule} from "@angular/forms";
import {ActivatedRoute, Router, RouterLink} from "@angular/router";
import {AppConfigService} from "@app/services/root/app-config.service";
import {TipService} from "@app/shared/services/tip-service";
import {NgbModal, NgbTooltipModule, NgbDropdown, NgbDropdownToggle, NgbDropdownMenu} from "@ng-bootstrap/ng-bootstrap";
import {AppDataService} from "@app/app-data.service";
import {ReceiverTipService} from "@app/services/helper/receiver-tip.service";
import {GrantAccessComponent} from "@app/shared/modals/grant-access/grant-access.component";
import {WhistleblowerMessagesComponent} from "@app/shared/modals/whistleblower-messages/whistleblower-messages.component";
import {RevokeAccessComponent} from "@app/shared/modals/revoke-access/revoke-access.component";
import {PreferenceResolver} from "@app/shared/resolvers/preference.resolver";
import {HttpService} from "@app/shared/services/http.service";
import {TabsComponent} from "@app/shared/components/tabs/tabs.component";
import {TabDirective} from "@app/shared/components/tabs/tab.directive";
import {UtilsService} from "@app/shared/services/utils.service";
import {TitleService} from "@app/shared/services/title.service";
import {Observable} from "rxjs";
import {
  TipOperationSetReminderComponent
} from "@app/shared/modals/tip-operation-set-reminder/tip-operation-set-reminder.component";
import {DeleteConfirmationComponent} from "@app/shared/modals/delete-confirmation/delete-confirmation.component";
import {
  TipOperationPostponeComponent
} from "@app/shared/modals/tip-operation-postpone/tip-operation-postpone.component";
import {CryptoService} from "@app/shared/services/crypto.service";
import {TransferAccessComponent} from "@app/shared/modals/transfer-access/transfer-access.component";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {ForwardReport, RecieverTipData} from "@app/models/receiver/receiver-tip-data";
import {Receiver} from "@app/models/app/public-model";
import {ReopenSubmissionComponent} from "@app/shared/modals/reopen-submission/reopen-submission.component";
import {ChangeSubmissionStatusComponent} from "@app/shared/modals/change-submission-status/change-submission-status.component";
import {TranslateService, TranslateModule} from "@ngx-translate/core";
import {TipInfoComponent} from "@app/shared/partials/tip-info/tip-info.component";
import {TipReceiverListComponent} from "@app/shared/partials/tip-receiver-list/tip-receiver-list.component";
import {TipQuestionnaireAnswersComponent} from "@app/shared/partials/tip-questionnaire-answers/tip-questionnaire-answers.component";
import {WhistleBlowerIdentityReceiverComponent} from "../whistleblower-identity-receiver/whistleblower-identity-receiver.component";
import {TipFilesReceiverComponent} from "@app/shared/partials/tip-files-receiver/tip-files-receiver.component";
import {TipUploadWbFileComponent as TipUploadWbFileComponent_1} from "../../../shared/partials/tip-upload-wbfile/tip-upload-wb-file.component";
import {TipCommentsComponent as TipCommentsComponent_1} from "../../../shared/partials/tip-comments/tip-comments.component";
import {TipAuditLogComponent} from "@app/shared/modals/tip-audit-log/tip-audit-log.component";
import {AccessCodeComponent} from "@app/shared/modals/access-code/access-code.component";
import {ForwardReportComponent} from "@app/shared/modals/forward-report/forward-report.component";
import {ConfirmationComponent} from "@app/shared/modals/confirmation/confirmation.component";
import {DatePipe} from "@angular/common";
import {CollapsiblePanelComponent} from "@app/shared/components/collapsible-panel/collapsible-panel.component";


@Component({
    selector: "src-tip",
    templateUrl: "./tip.component.html",
    standalone: true,
    imports: [
      TabsComponent,
      TabDirective,
      FormsModule,
      TipInfoComponent,
      TipReceiverListComponent,
      TipQuestionnaireAnswersComponent,
      WhistleBlowerIdentityReceiverComponent,
      TipFilesReceiverComponent,
      NgbTooltipModule,
      NgbDropdown,
      NgbDropdownToggle,
      NgbDropdownMenu,
      TipUploadWbFileComponent_1,
      TipCommentsComponent_1,
      DatePipe,
      RouterLink,
      CollapsiblePanelComponent,
      TranslateModule
    ],
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
  protected appDataService = inject(AppDataService);
  protected RTipService = inject(ReceiverTipService);
  protected authenticationService = inject(AuthenticationService);
  private titleService = inject(TitleService);


  tip_id: string | null;
  tip: RecieverTipData;
  score: number;
  ctx: string;
  showEditLabelInput: boolean;
  loading = true;
  forwardsCollapsed = false;
  redactMode:boolean = false;
  redactOperationTitle: string;
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
          if (!response) {
            return;
          }
          // The report may reference a context hidden from the public listing;
          // resolve it on demand so its metadata is available for display.
          this.appConfigServices.loadContext(response.context_id).subscribe(() => {
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
            if (this.tip.type === 'forward') {
              this.appDataService.header_title = "Forward";
              this.titleService.setTitle();
            } else if (this.tip.type === 'forward-request') {
              this.appDataService.header_title = "Forward request";
              this.titleService.setTitle();
            }
            this.cdr.markForCheck();
          });
        }
      }
    );
  }

  // The recipients following the forward from the tenant that performed it
  // walk back to the report it originates from; everyone else walks back to
  // the list of the reports
  backLink() {
    if (this.tip?.type === "forward" && this.tip.forwarding?.internaltip_id) {
      return ["/reports", this.tip.forwarding.internaltip_id];
    }

    return ["/recipient/reports"];
  }

  // The tenant on the other side of the forward relative to the viewer
  openForwardedReport(id: string) {
    this.router.navigate(["/reports", id]);
  }

  // The tenant that receives a forward decides whether the sender keeps
  // accessing it: the row opens only when the viewer holds that access
  canOpenForwardedReport(forward: ForwardReport) {
    return !!forward.accessible;
  }

  // The space shared with the counterpart of the report: the whistleblower,
  // or the receiving tenant when the report is a forward performed from here
  everyoneKey(): string {
    return this.tip?.type === "forward" ? "forward" : "public";
  }

  isReceivedForward() {
    return this.tip?.type === "forward" && !!this.tip.forwarding &&
           !this.tip.forwarding.internaltip_id;
  }

  canMessageWhistleblower() {
    return this.isReceivedForward() && !!this.tip.forwarding?.messages_enabled;
  }

  openWhistleblowerMessagesModal() {
    const modalRef = this.modalService.open(WhistleblowerMessagesComponent, {size: "lg"});
    modalRef.componentInstance.tipService = this.RTipService;
  }

  // A report belongs to the recipients of the tenant it is filed on, that
  // operate it as they operate any report of their whistleblowers; the
  // recipients reading it from the other side of a forward take part in its
  // exchanges and never operate it
  ownsReport() {
    return !!this.tip?.owned;
  }

  canChangeStatus() {
    return this.preferencesService.dataModel.profile.permissions.can_change_status &&
           this.ownsReport();
  }

  canChangeLabel() {
    return this.preferencesService.dataModel.profile.permissions.can_change_label &&
           this.ownsReport();
  }

  canSetReminder() {
    return this.ownsReport();
  }

  canMarkImportant() {
    return this.ownsReport();
  }

  isTenantForwardRequest() {
    return this.preferencesService.dataModel.tid !== 1 &&
           Number(this.tip?.data?.forward_request?.source_tid) === this.preferencesService.dataModel.tid;
  }

  isTenantForwardRequestAuthorized() {
    return this.isTenantForwardRequest() && !!this.tip?.allow_forward;
  }

  canForwardReport() {
    return this.preferencesService.dataModel.profile.permissions.can_forward_reports &&
           !!this.tip?.can_forward;
  }

  hasActions() {
    // The gear is offered only when it opens on something: the reports of the
    // forwarding workflow leave no action at all to the tenant that follows them
    return this.canEditExpiration() ||
           this.canMaskOrRedact() ||
           this.canChangeStatus() ||
           this.canForwardReport() ||
           this.canAuthorizeForward() ||
           this.canDenyForward() ||
           this.canMessageWhistleblower() ||
           this.canGetAccessCode() ||
           this.canDeleteReport();
  }

  // The recipients of the tenant that received the request decide on it; the
  // tenant that issued it follows the outcome without deciding it
  decidesOnForwardRequest() {
    return this.tip?.type === "forward-request" && !this.isTenantForwardRequest();
  }

  canGetAccessCode() {
    // The receipt handed over to the whistleblower is offered to the tenant that
    // performed the forward until the whistleblower replaces it with its own
    return this.isTenantForwardRequest() &&
           !!this.tip?.data?.forward_receipt &&
           !!this.tip?.forward_receipt_valid;
  }

  getAccessCode() {
    const modalRef = this.modalService.open(AccessCodeComponent, {
      backdrop: "static",
      keyboard: false,
      ariaLabelledBy: "modal-title"
    });
    modalRef.componentInstance.code = this.tip?.data?.forward_receipt || "";
  }

  canAuthorizeForward() {
    return this.decidesOnForwardRequest() && !this.tip?.allow_forward;
  }

  canDenyForward() {
    return this.decidesOnForwardRequest() && this.tip?.status !== "closed";
  }

  // Until it is decided the request lives its ordinary lifecycle and reports
  // the status of any other report
  hasForwardRequestStatus() {
    return !!this.tip?.data?.forward_request &&
           (!!this.tip?.allow_forward || this.tip?.status === "closed");
  }

  forwardRequestStatusLabel() {
    if (!this.hasForwardRequestStatus()) {
      return "";
    }

    return this.tip?.allow_forward ? "Authorized" : "Denied";
  }

  forwardRequestStatusClass() {
    return this.tip?.allow_forward ? "bg-success" : "bg-danger";
  }

  canEditExpiration() {
    return !!this.tip?.context &&
           this.preferencesService.dataModel.profile.permissions.can_postpone_expiration &&
           this.ownsReport();
  }

  canDeleteReport() {
    const permissions = this.preferencesService.dataModel.profile.permissions;

    return permissions.can_delete_submission &&
           this.ownsReport();
  }

  canMaskOrRedact() {
    const permissions = this.preferencesService.dataModel.profile.permissions;

    return (permissions.can_redact_information || permissions.can_mask_information) &&
           this.ownsReport();
  }

  updateLabel(label: string) {
    if (!this.canChangeLabel()) {
      return;
    }

    this.httpService.tipOperation("set", {"key": "label", "value": label}, this.RTipService.tip.id).subscribe();
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
                this.httpService.tipOperation(req.operation, req.args, this.tip.id)
                  .subscribe(() => {
                    this.router.navigate(["recipient", "reports"]).then();
                  });
              }
            },
            () => {
              // The transfer modal was dismissed: nothing to do.
            }
          );
        }
      }
    );
  }

  openForwardModal() {
    this.httpService.requestForwardOptions(this.tip.id).subscribe((response: any) => {
      const modalRef = this.modalService.open(ForwardReportComponent, {
        size: 'xl',
        backdrop: 'static',
        keyboard: false
      });
      modalRef.componentInstance.tipId = this.tip.id;
      modalRef.componentInstance.tenants = response.tenants;
      modalRef.componentInstance.selectedTenant = response.target_tid;
      modalRef.componentInstance.questionnaire = response.questionnaire;
      modalRef.componentInstance.showTenantSelector = this.preferencesService.dataModel.tid === 1;
      // The forward performed on a request of forward is not accessible to the
      // tenant that performed it: its interface on the matter stays the request
      modalRef.componentInstance.navigateOnSuccess = this.tip.type !== "forward-request";
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
    modalRef.componentInstance.message = "By confirming, the tenant that issued this request will be allowed to perform a forward.";
    modalRef.componentInstance.confirmLabel = "Authorize";
    modalRef.componentInstance.confirmFunction = () => {
      const req = {
        operation: "set",
        args: {
          key: "allow_forward",
          value: true
        }
      };

      this.httpService.tipOperation(req.operation, req.args, this.tip.id).subscribe(() => {
        this.reload();
      });
    };
  }

  denyForward() {
    const modalRef = this.modalService.open(ConfirmationComponent, {
      backdrop: 'static',
      keyboard: false,
      ariaLabelledBy: 'modal-title'
    });
    modalRef.componentInstance.title = "Deny forward";
    modalRef.componentInstance.message = "By confirming, this request of forward will be closed and denied.";
    modalRef.componentInstance.confirmLabel = "Deny";
    modalRef.componentInstance.confirmFunction = () => {
      const req = {
        operation: "set",
        args: {
          key: "allow_forward",
          value: false
        }
      };

      this.httpService.tipOperation(req.operation, req.args, this.tip.id).subscribe(() => {
        this.reload();
      });
    };
  }

  openModalChangeState(){
    if (!this.canChangeStatus()) {
      return;
    }

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
    if (!this.canChangeStatus()) {
      return;
    }

    const modalRef = this.modalService.open(ReopenSubmissionComponent, {backdrop: 'static', keyboard: false});
    modalRef.componentInstance.confirmFunction = () => {
      this.tip.status = "opened";
      this.tip.substatus = "";
      this.updateSubmissionStatus();
    };
    modalRef.componentInstance.cancelFun = null;
  }

  updateSubmissionStatus() {
    if (!this.canChangeStatus()) {
      return;
    }

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
    if (!this.canMarkImportant()) {
      return;
    }

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
    if (!this.canDeleteReport()) {
      return;
    }

    const modalRef = this.modalService.open(DeleteConfirmationComponent, {backdrop: 'static', keyboard: false});
    modalRef.componentInstance.confirmFunction = () => {
      // The modal performs the deletion itself through args.
    };
    modalRef.componentInstance.args = {
      tip: this.RTipService.tip,
      operation: "delete"
    };
  }

  setReminder() {
    if (!this.canSetReminder()) {
      return;
    }

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
    this.utils.saveAs(this.authenticationService, "tip.zip", `/api/recipient/rtips/${tipId}/export`);
  }

  openLogsModal() {
    const modalRef = this.modalService.open(TipAuditLogComponent, {
      size: 'xl',
      backdrop: 'static',
      keyboard: false
    });

    modalRef.componentInstance.tipId = this.tip_id;
    modalRef.componentInstance.tipData = this.tip;
    modalRef.componentInstance.usersData = this.tip?.receivers || [];
  }

  toggleRedactMode() {
    if (!this.canMaskOrRedact()) {
      this.redactMode = false;
      return;
    }

    this.redactMode = !this.redactMode;
  }

  listenToFields() {
    this.loadTipData();
  }

  protected readonly JSON = JSON;
}
