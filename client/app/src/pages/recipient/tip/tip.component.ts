import {ChangeDetectorRef, Component, OnInit, inject} from "@angular/core";
import {FormsModule} from "@angular/forms";
import {ActivatedRoute, Router, RouterLink} from "@angular/router";
import {AppConfigService} from "@app/services/root/app-config.service";
import {TipService} from "@app/shared/services/tip-service";
import {NgbModal, NgbTooltipModule, NgbDropdown, NgbDropdownToggle, NgbDropdownMenu} from "@ng-bootstrap/ng-bootstrap";
import {AppDataService} from "@app/app-data.service";
import {ReceiverTipService} from "@app/services/helper/receiver-tip.service";
import {GrantAccessComponent} from "@app/shared/modals/grant-access/grant-access.component";
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
import {TransferAccessComponent} from "@app/shared/modals/transfer-access/transfer-access.component";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {ExchangeReport, RecieverTipData} from "@app/models/receiver/receiver-tip-data";
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
import {ExchangeReportComponent} from "@app/shared/modals/exchange-report/exchange-report.component";
import {ConfirmationComponent} from "@app/shared/modals/confirmation/confirmation.component";
import {
  RequestAdditionalQuestionnaireComponent
} from "@app/shared/modals/request-additional-questionnaire/request-additional-questionnaire.component";
import {DatePipe} from "@angular/common";
import {CollapsiblePanelComponent} from "@app/shared/components/collapsible-panel/collapsible-panel.component";
import {
  TipAdditionalQuestionnaireInviteComponent
} from "@app/shared/partials/tip-additional-questionnaire-invite/tip-additional-questionnaire-invite.component";


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
      TipAdditionalQuestionnaireInviteComponent,
      TranslateModule
    ],
})
export class TipComponent implements OnInit {
  private readonly translateService = inject(TranslateService);
  private readonly tipService = inject(TipService);
  private readonly appConfigServices = inject(AppConfigService);
  private readonly router = inject(Router);
  private readonly cdr = inject(ChangeDetectorRef);
  protected utils = inject(UtilsService);
  protected preferencesService = inject(PreferenceResolver);
  protected modalService = inject(NgbModal);
  private readonly activatedRoute = inject(ActivatedRoute);
  protected httpService = inject(HttpService);
  protected appDataService = inject(AppDataService);
  protected RTipService = inject(ReceiverTipService);
  protected authenticationService = inject(AuthenticationService);
  private readonly titleService = inject(TitleService);


  tip_id: string | null;
  tip: RecieverTipData;
  score: number;
  ctx: string;
  showEditLabelInput: boolean;
  loading = true;
  communicationsCollapsed = false;
  redactMode = false;
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
            if (this.tip.type === 'exchange') {
              this.appDataService.header_title =
                this.tip.exchange?.type === 'communication' ? "Communication" : "Transmission";
              this.titleService.setTitle();
            } else if (this.tip.type === 'request') {
              this.appDataService.header_title = "Request";
              this.titleService.setTitle();
            }
            this.cdr.markForCheck();
          });
        }
      }
    );
  }

  // The recipients of the filing site walk back to the report of origin; everyone else to the list
  backLink() {
    if (this.tip?.type === "exchange" && this.tip.exchange?.internaltip_id) {
      return ["/reports", this.tip.exchange.internaltip_id];
    }

    return ["/recipient/reports"];
  }

  openExchangedReport(id: string) {
    void this.router.navigate(["/reports", id]);
  }

  // The row opens for the recipients that follow what was filed
  canOpenExchangedReport(entry: ExchangeReport) {
    return !!entry.accessible;
  }

  // The report belongs to the recipients of the tenant it is filed on; the other side reads it and
  // operates nothing
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

  // Something to decide: questionnaires the channel names, or one already asked
  canRequestAdditionalQuestionnaire() {
    return !!this.tip?.additional_questionnaire_requestable;
  }

  // What is asked stands until answered or withdrawn, and is shown to both sides
  shouldShowAdditionalQuestionnaire(): boolean {
    return this.canRequestAdditionalQuestionnaire() && !!this.tip?.additional_questionnaire_id;
  }

  // The one already asked comes chosen: confirming nothing withdraws it, another replaces it
  requestAdditionalQuestionnaire() {
    if (!this.canRequestAdditionalQuestionnaire()) {
      return;
    }

    this.httpService.requestRecipientTipQuestionnaires(this.tip.id).subscribe(questionnaires => {
      const modalRef = this.modalService.open(RequestAdditionalQuestionnaireComponent, {backdrop: 'static', keyboard: false});
      modalRef.componentInstance.selectableQuestionnaires = questionnaires;
      modalRef.componentInstance.requestedId = this.tip.additional_questionnaire_id || "";
      modalRef.result.then(
        (decision: {questionnaire: string}) => {
          this.httpService.tipOperation("request_additional_questionnaire", {questionnaire: decision.questionnaire}, this.tip.id)
            .subscribe(() => {
              this.reload();
            });
        },
        () => { /* dismissed */ }
      );
    });
  }

  // Followed by the site that filed it, decided by the one it is addressed to
  isTenantRequest() {
    return Number(this.tip?.data?.request?.source_tid) === this.preferencesService.dataModel.tid;
  }

  // Carried by the recipients allowed to communicate, where a communication runs
  canCommunicate() {
    return this.preferencesService.dataModel.profile.permissions.can_send_communications &&
           !!this.tip?.can_communicate;
  }

  hasActions() {
    // Offered only when it opens on something: the following tenant has no action
    return this.canEditExpiration() ||
           this.canMaskOrRedact() ||
           this.canChangeStatus() ||
           this.canCommunicate() ||
           this.canAuthorizeTransmission() ||
           this.canDenyTransmission() ||
           this.canRequestAdditionalQuestionnaire() ||
           this.canGetAccessCode() ||
           this.canDeleteReport();
  }

  // Decided by the receiving site; the asking one follows; a recipient never decides its own request
  decidesOnTransmissionRequest() {
    return !!this.tip?.can_decide_request;
  }

  canGetAccessCode() {
    // Offered to the transmitting tenant until the whistleblower replaces the receipt
    return this.isTenantRequest() &&
           !!this.tip?.data?.receipt &&
           !!this.tip?.receipt_valid;
  }

  getAccessCode() {
    const modalRef = this.modalService.open(AccessCodeComponent, {
      backdrop: "static",
      keyboard: false,
      ariaLabelledBy: "modal-title"
    });
    modalRef.componentInstance.code = this.tip?.data?.receipt || "";
  }

  // A decided request is not decided again
  canAuthorizeTransmission() {
    return this.decidesOnTransmissionRequest() && !this.tip?.allow_transmission &&
           this.tip?.status !== "closed";
  }

  canDenyTransmission() {
    return this.decidesOnTransmissionRequest() && this.tip?.status !== "closed";
  }

  // Until decided, the request has the ordinary status
  hasRequestStatus() {
    return !!this.tip?.data?.request &&
           (!!this.tip?.allow_transmission || this.tip?.status === "closed");
  }

  transmissionRequestStatusLabel() {
    if (!this.hasRequestStatus()) {
      return "";
    }

    return this.tip?.allow_transmission ? "Authorized" : "Denied";
  }

  transmissionRequestStatusClass() {
    return this.tip?.allow_transmission ? "bg-success" : "bg-danger";
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
        this.appDataService.public.receivers.forEach((receiver: Receiver) => {
          if (receiver.id !== this.authenticationService.session?.user_id && !this.tip.receivers_by_id[receiver.id]) {
            receiver.name = names[receiver.id] ?? receiver.name;
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
          this.appDataService.public.receivers.forEach((receiver: Receiver) => {
            if (receiver.id !== this.authenticationService.session?.user_id && this.tip.receivers_by_id[receiver.id]) {
              receiver.name = names[receiver.id] ?? receiver.name;
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
          this.appDataService.public.receivers.forEach((receiver: Receiver) => {
            if (receiver.id !== this.authenticationService.session?.user_id && !this.tip.receivers_by_id[receiver.id]) {
              receiver.name = names[receiver.id] ?? receiver.name;
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
                    void this.router.navigate(["recipient", "reports"]);
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

  // The site and the channel are chosen in the modal, which composes the questionnaire
  openCommunicationModal() {
    const modalRef = this.modalService.open(ExchangeReportComponent, {
      size: 'xl',
      backdrop: 'static',
      keyboard: false
    });
    modalRef.componentInstance.tipId = this.tip.id;
    modalRef.componentInstance.title = "Communication";
    modalRef.result.then(
      () => this.reload(),
      () => { /* dismissed */ }
    );
  }

  authorizeTransmission() {
    const modalRef = this.modalService.open(ConfirmationComponent, {
      backdrop: 'static',
      keyboard: false,
      ariaLabelledBy: 'modal-title'
    });
    modalRef.componentInstance.title = "Authorize the report";
    modalRef.componentInstance.message = "By confirming, the site that issued this request will be allowed to file the report it asked for.";
    modalRef.componentInstance.confirmLabel = "Authorize";
    modalRef.componentInstance.confirmFunction = () => {
      const req = {
        operation: "set",
        args: {
          key: "allow_transmission",
          value: true
        }
      };

      this.httpService.tipOperation(req.operation, req.args, this.tip.id).subscribe(() => {
        this.reload();
      });
    };
  }

  denyTransmission() {
    const modalRef = this.modalService.open(ConfirmationComponent, {
      backdrop: 'static',
      keyboard: false,
      ariaLabelledBy: 'modal-title'
    });
    modalRef.componentInstance.title = "Deny the report";
    modalRef.componentInstance.message = "By confirming, this request of transmission will be closed and denied.";
    modalRef.componentInstance.confirmLabel = "Deny";
    modalRef.componentInstance.confirmFunction = () => {
      const req = {
        operation: "set",
        args: {
          key: "allow_transmission",
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
      submission_statuses:this.prepareSubmissionStatuses()
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

    const args: any = {"status":  this.tip.status, "substatus": this.tip.substatus ? this.tip.substatus : ""};
    this.httpService.tipOperation("update_status", args, this.tip.id)
      .subscribe(
        () => {
          this.reload();
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

  // A transmitter files reports and holds none
  isTransmitter(): boolean {
    return this.authenticationService.session?.role === "transmitter";
  }

  showPersonalNotes(): boolean {
    return !this.isTransmitter();
  }

  // The space the recipients share among themselves has no place on a report a
  // single recipient holds: there is nobody there to speak with. It is kept all
  // the same where something was already exchanged in it, so that what was said
  // with the recipients that have since been removed does not leave with them.
  showRecipientsOnly(): boolean {
    if (!this.tip || this.isTransmitter()) {
      return false;
    }

    if (this.tip.receivers.filter(receiver => receiver.active).length > 1) {
      return true;
    }

    return this.tip.comments.some(comment => comment.visibility === "internal") ||
           this.tip.rfiles.some(rfile => rfile.visibility === "internal");
  }

  /**
   * Read the report again.
   *
   * What changes on this page - the recipients it is granted to, the dates it
   * carries - is read back by asking for the report, not by leaving the route
   * and entering it again: navigating away and back races with whoever else is
   * navigating, and reloadComponent() disables the reuse of every route of the
   * session on its way.
   */
  reload(): void {
    this.loadTipData();
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
