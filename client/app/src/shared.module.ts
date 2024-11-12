import {NgModule} from "@angular/core";
import {CommonModule, NgOptimizedImage} from "@angular/common";
import {FooterComponent} from "@app/shared/partials/footer/footer.component";
import {ReceiptComponent} from "@app/shared/partials/receipt/receipt.component";
import {FormsModule, ReactiveFormsModule} from "@angular/forms";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {Enable2fa} from "@app/shared/partials/enable-2fa/enable-2fa";
import {TranslateModule} from "@ngx-translate/core";
import {QRCodeModule} from "angularx-qrcode";
import {PasswordChangeComponent} from "@app/shared/partials/password-change/password-change.component";
import {PasswordMeterComponent} from "@app/shared/components/password-meter/password-meter.component";
import { NgbPagination,NgbPaginationFirst,NgbPaginationLast,NgbPaginationNext,NgbPaginationNumber,NgbPaginationPages,NgbPaginationPrevious,NgbNav,NgbNavItem,NgbNavLink,NgbNavContent,NgbProgressbar,NgbDatepickerModule,NgbDropdownModule,NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {PrivacyBadgeComponent} from "@app/shared/partials/privacybadge/privacy-badge.component";
import {MarkdownModule} from "ngx-markdown";
import {StripHtmlPipe} from "@app/shared/pipes/strip-html.pipe";
import {ReceiptValidatorDirective} from "@app/shared/directive/receipt-validator.directive";
import {TipInfoComponent} from "@app/shared/partials/tip-info/tip-info.component";
import {NgSelectModule} from "@ng-select/ng-select";
import {TipAdditionalQuestionnaireInviteComponent} from "@app/shared/partials/tip-additional-questionnaire-invite/tip-additional-questionnaire-invite.component";
import {TipFieldComponent} from "@app/shared/partials/tip-field/tip-field.component";
import {TipFieldAnswerEntryComponent} from "@app/shared/partials/tip-field-answer-entry/tip-field-answer-entry.component";
import {TipQuestionnaireAnswersComponent} from "@app/shared/partials/tip-questionnaire-answers/tip-questionnaire-answers.component";
import {DatePipe} from "@app/shared/pipes/date.pipe";
import {SplitPipe} from "@app/shared/pipes/split.pipe";
import {TipFilesWhistleblowerComponent} from "@app/shared/partials/tip-files-whistleblower/tip-files-whistleblower.component";
import {WidgetWbFilesComponent} from "@app/shared/partials/widget-wbfiles/widget-wb-files.component";
import {ByteFmtPipe} from "@app/shared/pipes/byte-fmt.pipe";
import {RFileUploadButtonComponent} from "@app/shared/partials/rfile-upload-button/r-file-upload-button.component";
import {RFileUploadStatusComponent} from "@app/shared/partials/rfile-upload-status/r-file-upload-status.component";
import {TipCommentsComponent} from "@app/shared/partials/tip-comments/tip-comments.component";
import {LimitToPipe} from "@app/shared/pipes/limit-to.pipe";
import {OrderByPipe} from "@app/shared/pipes/order-by.pipe";
import {TipReceiverListComponent} from "@app/shared/partials/tip-receiver-list/tip-receiver-list.component";
import {FilterPipe} from "@app/shared/pipes/filter.pipe";
import {RequestSupportComponent} from "@app/shared/modals/request-support/request-support.component";
import {NgxFlowModule} from "@flowjs/ngx-flow";
import {RFilesUploadStatusComponent} from "@app/shared/partials/rfiles-upload-status/r-files-upload-status.component";
import {NgFormChangeDirective} from "@app/shared/directive/ng-form-change.directive";
import {WbFilesComponent} from "@app/shared/partials/wbfiles/wb-files.component";
import {DisableCcpDirective} from "@app/shared/directive/disable-ccp.directive";
import {SubdomainValidatorDirective} from "@app/shared/directive/subdomain-validator.directive";
import {PasswordStrengthValidatorDirective} from "@app/shared/directive/password-strength-validator.directive";
import {UserHomeComponent} from "@app/shared/partials/user-home/user-home.component";
import {UserWarningsComponent} from "@app/shared/partials/user-warnings/user-warnings.component";
import {GrantAccessComponent} from "@app/shared/modals/grant-access/grant-access.component";
import {RevokeAccessComponent} from "@app/shared/modals/revoke-access/revoke-access.component";
import {DeleteConfirmationComponent} from "@app/shared/modals/delete-confirmation/delete-confirmation.component";
import {DateRangeSelectorComponent} from "@app/shared/components/date-selector/date-selector.component";
import {PreferencesComponent} from "@app/shared/partials/preferences/preferences.component";
import {PreferenceTab1Component} from "@app/shared/partials/preference-tabs/preference-tab1/preference-tab1.component";
import {PreferenceTab2Component} from "@app/shared/partials/preference-tabs/preference-tab2/preference-tab2.component";
import {Enable2faComponent} from "@app/shared/modals/enable2fa/enable2fa.component";
import {EncryptionRecoveryKeyComponent} from "@app/shared/modals/encryption-recovery-key/encryption-recovery-key.component";
import {ConfirmationWithPasswordComponent} from "@app/shared/modals/confirmation-with-password/confirmation-with-password.component";
import {ConfirmationWith2faComponent} from "@app/shared/modals/confirmation-with2fa/confirmation-with2fa.component";
import {TipOperationFileIdentityAccessRequestComponent} from "@app/shared/modals/tip-operation-file-identity-access-request/tip-operation-file-identity-access-request.ompoent";
import {TipFilesReceiverComponent} from "@app/shared/partials/tip-files-receiver/tip-files-receiver.component";
import {TipOperationSetReminderComponent} from "@app/shared/modals/tip-operation-set-reminder/tip-operation-set-reminder.component";
import {TipOperationPostponeComponent} from "@app/shared/modals/tip-operation-postpone/tip-operation-postpone.component";
import {FileViewComponent} from "@app/shared/modals/file-view/file-view.component";
import {TipUploadWbFileComponent} from "@app/shared/partials/tip-upload-wbfile/tip-upload-wb-file.component";
import {ImageUploadDirective} from "@app/shared/directive/image-upload.directive";
import {ImageUploadComponent} from "@app/shared/partials/image-upload/image-upload.component";
import {EnableEncryptionComponent} from "@app/shared/modals/enable-encryption/enable-encryption.component";
import {AdminFileComponent} from "@app/shared/partials/admin-file/admin-file.component";
import {ConfirmationComponent} from "@app/shared/modals/confirmation/confirmation.component";
import {QuestionnaireDuplicationComponent} from "@app/shared/modals/questionnaire-duplication/questionnaire-duplication.component";
import {AddOptionHintComponent} from "@app/shared/modals/add-option-hint/add-option-hint.component";
import {TriggerReceiverComponent} from "@app/shared/modals/trigger-receiver/trigger-receiver.component";
import {AssignScorePointsComponent} from "@app/shared/modals/assign-score-points/assign-score-points.component";
import {TipOperationFileIdentityAccessReplyComponent} from "@app/shared/modals/tip-operation-file-identity-access-reply/tip-operation-file-identity-access-reply.component";
import {DemoComponent} from "@app/shared/partials/demo/demo.component";
import {MessageConsoleComponent} from "@app/shared/partials/messageconsole/message-console.component";
import {AcceptAgreementComponent} from "@app/shared/modals/accept-agreement/accept-agreement.component";
import {DisclaimerComponent} from "@app/shared/modals/disclaimer/disclaimer.component";
import {TransferAccessComponent} from "@app/shared/modals/transfer-access/transfer-access.component";
import {BlankComponent} from "@app/shared/blank/blank.component";
import {VoiceRecorderComponent} from "@app/shared/partials/voice-recorder/voice-recorder.component";
import {Tab1Component} from "@app/pages/admin/settings/tab1/tab1.component";
import {SwitchComponent} from "@app/shared/components/switch/switch.component";
import {ChangeSubmissionStatusComponent} from "@app/shared/modals/change-submission-status/change-submission-status.component";
import {ReopenSubmissionComponent} from "@app/shared/modals/reopen-submission/reopen-submission.component";
import {OtkcAccessComponent} from "@app/shared/modals/otkc-access/otkc-access.component";
import {OperationComponent} from "@app/shared/partials/operation/operation.component";
import {RedactInformationComponent} from "@app/shared/modals/redact-information/redact-information.component";
import { DownloadConfirmationComponent } from "./shared/modals/download-confirmation/download-confirmation.component";
import { OrgInfoComponent } from "@app/shared/partials/org-info/org-info.component";
import { OrgAdminInfoComponent } from "@app/shared/partials/org-admin-info/org-admin-info.component";
import { OrgRecipientInfoComponent } from "@app/shared/partials/org-recipient-info/org-recipient-info.component";
import { OrgOverviewComponent } from "@app/shared/partials/org-overview/org-overview.component";
import { OrgUsersListComponent } from "@app/shared/partials/org-users-list/org-users-list.component";
import { CustomModalComponent } from "./shared/modals/custom-modal/custom-modal.component";
import { SendtipFilesComponent } from "@app/shared/partials/sendtip-files/sendtip-files.component";
import { SendTipFileUploadComponent } from "@app/shared/partials/sendtip-file-upload/sendtip-file-upload.component";
import { TipEoListComponent } from "@app/shared/partials/tip-eo-list/tip-eo-list.component";
import { TipEoFormComponent } from "@app/shared/partials/tip-eo-form/tip-eo-form.component";
import { SelectEODropdownComponent } from "@app/shared/partials/selecteo-dropdown/selecteo-dropdown.component";
import { TipEoCommentsComponent } from "./shared/partials/tip-eo-comments/tip-eo-comments.component";
import { TipEoRfilesReceiverComponent } from "./shared/partials/tip-eo-rfiles-receiver/tip-eo-rfiles-receiver.component";
import { SendtipDetailQuestionnaireAnswersComponent } from "./shared/partials/sendtip-detail-questionnaire-answers/sendtip-detail-questionnaire-answers.component";
import { TipFieldQuestionEntryComponent } from "./shared/partials/tip-field-question-entry/tip-field-question-entry.component";

@NgModule({
  imports: [
    CommonModule,
    TranslateModule,
    FormsModule,
    QRCodeModule,
    ReactiveFormsModule,
    NgbProgressbar,
    MarkdownModule,
    NgSelectModule,
    NgbPagination,
    NgbPaginationPrevious,
    NgbPaginationNext,
    NgbPaginationFirst,
    NgbPaginationLast,
    NgbPaginationNumber,
    NgbPaginationPages,
    NgxFlowModule,
    NgbDatepickerModule,
    NgbDropdownModule,
    DateRangeSelectorComponent,
    NgbNav,
    NgbNavItem,
    NgbNavLink,
    NgbNavContent,
    NgbDropdownModule,
    NgbTooltipModule,
    NgOptimizedImage,
  ],
  declarations: [
    FooterComponent,
    ReceiptComponent,
    TranslatorPipe,
    Enable2fa,
    PasswordChangeComponent,
    PasswordMeterComponent,
    PrivacyBadgeComponent,
    StripHtmlPipe,
    DatePipe,
    ReceiptValidatorDirective,
    TipInfoComponent,
    TipEoFormComponent,
    TipQuestionnaireAnswersComponent,
    SendtipDetailQuestionnaireAnswersComponent,
    TipAdditionalQuestionnaireInviteComponent,
    TipFieldComponent,
    TipFieldAnswerEntryComponent,
    TipFieldQuestionEntryComponent,
    DatePipe,
    SplitPipe,
    TipFilesWhistleblowerComponent,
    WidgetWbFilesComponent,
    ByteFmtPipe,
    RFileUploadButtonComponent,
    RFileUploadStatusComponent,
    TipCommentsComponent,
    TipEoCommentsComponent,
    LimitToPipe,
    OrderByPipe,
    TipReceiverListComponent,
    FilterPipe,
    RequestSupportComponent,
    RFilesUploadStatusComponent,
    NgFormChangeDirective,
    WbFilesComponent,
    DisableCcpDirective,
    SubdomainValidatorDirective,
    PasswordStrengthValidatorDirective,
    PasswordStrengthValidatorDirective,
    ImageUploadDirective,
    ImageUploadComponent,
    UserHomeComponent,
    UserWarningsComponent,
    GrantAccessComponent,
    RevokeAccessComponent,
    DeleteConfirmationComponent,
    PreferencesComponent,
    PreferenceTab1Component,
    PreferenceTab2Component,
    Enable2faComponent,
    EncryptionRecoveryKeyComponent,
    ConfirmationWithPasswordComponent,
    ConfirmationWith2faComponent,
    TipOperationFileIdentityAccessRequestComponent,
    TipFilesReceiverComponent,
    TipEoRfilesReceiverComponent,
    TipEoListComponent,
    SendtipFilesComponent,
    SendTipFileUploadComponent,
    TipOperationSetReminderComponent,
    TipOperationPostponeComponent,
    FileViewComponent,
    TipUploadWbFileComponent,
    EnableEncryptionComponent,
    AdminFileComponent,
    ConfirmationComponent,
    QuestionnaireDuplicationComponent,
    AddOptionHintComponent,
    TriggerReceiverComponent,
    AssignScorePointsComponent,
    TipOperationFileIdentityAccessReplyComponent,
    DemoComponent,
    MessageConsoleComponent,
    MessageConsoleComponent,
    AcceptAgreementComponent,
    TransferAccessComponent,
    DisclaimerComponent,
    ChangeSubmissionStatusComponent,
    ReopenSubmissionComponent,
    BlankComponent,
    VoiceRecorderComponent,
    Tab1Component,
    SwitchComponent,
    OtkcAccessComponent,
    OperationComponent,
    RedactInformationComponent,
    SelectEODropdownComponent,
    DownloadConfirmationComponent,
    OrgInfoComponent,
    OrgRecipientInfoComponent,
    OrgAdminInfoComponent,
    OrgOverviewComponent,
    OrgUsersListComponent,
    CustomModalComponent
  ],
  exports: [
    FooterComponent,
    ReceiptComponent,
    TranslatorPipe,
    PrivacyBadgeComponent,
    Enable2fa,
    PasswordChangeComponent,
    StripHtmlPipe,
    FilterPipe,
    OrderByPipe,
    TipInfoComponent,
    TipEoFormComponent,
    TipQuestionnaireAnswersComponent,
    SendtipDetailQuestionnaireAnswersComponent,
    TipAdditionalQuestionnaireInviteComponent,
    TipFieldComponent,
    TipFilesWhistleblowerComponent,
    WidgetWbFilesComponent,
    TipCommentsComponent,
    TipEoCommentsComponent,
    TipReceiverListComponent,
    RFileUploadStatusComponent,
    RFileUploadButtonComponent,
    RFilesUploadStatusComponent,
    NgFormChangeDirective,
    DisableCcpDirective,
    SubdomainValidatorDirective,
    PasswordMeterComponent,
    PasswordStrengthValidatorDirective,
    ImageUploadDirective,
    ImageUploadComponent,
    UserHomeComponent,
    UserWarningsComponent,
    GrantAccessComponent,
    RevokeAccessComponent,
    DeleteConfirmationComponent,
    DownloadConfirmationComponent,
    DateRangeSelectorComponent,
    TipOperationFileIdentityAccessRequestComponent,
    TipFilesReceiverComponent,
    TipEoRfilesReceiverComponent,
    TipEoListComponent,
    SendtipFilesComponent,
    SendTipFileUploadComponent,
    TipOperationSetReminderComponent,
    TipUploadWbFileComponent,
    EnableEncryptionComponent,
    AdminFileComponent,
    ConfirmationComponent,
    QuestionnaireDuplicationComponent,
    AddOptionHintComponent,
    TriggerReceiverComponent,
    AssignScorePointsComponent,
    PreferencesComponent,
    DemoComponent,
    MessageConsoleComponent,
    AcceptAgreementComponent,
    TransferAccessComponent,
    DisclaimerComponent,
    ChangeSubmissionStatusComponent,
    ReopenSubmissionComponent,
    VoiceRecorderComponent,
    Tab1Component,
    SwitchComponent,
    OtkcAccessComponent,
    OperationComponent,
    RedactInformationComponent,
    SelectEODropdownComponent,
    OrgInfoComponent,
    OrgRecipientInfoComponent,
    OrgAdminInfoComponent,
    OrgOverviewComponent,
    OrgUsersListComponent,
    CustomModalComponent
  ]
})
export class SharedModule {
}
