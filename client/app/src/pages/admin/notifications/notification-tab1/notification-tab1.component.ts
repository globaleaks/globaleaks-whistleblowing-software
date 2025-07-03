import {Component, Input, inject} from "@angular/core";
import {NgForm, FormsModule} from "@angular/forms";
import {notificationResolverModel} from "@app/models/resolvers/notification-resolver-model";
import {Constants} from "@app/shared/constants/constants";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {NotificationsResolver} from "@app/shared/resolvers/notifications.resolver";
import {UtilsService} from "@app/shared/services/utils.service";
import {switchMap} from "rxjs";
import {NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {NgbNav, NgbNavItem, NgbNavItemRole, NgbNavLinkButton, NgbNavLinkBase, NgbNavContent, NgbNavOutlet} from "@ng-bootstrap/ng-bootstrap";
import {NgTemplateOutlet} from "@angular/common";
import {NgSelectComponent, NgOptionTemplateDirective} from "@ng-select/ng-select";
import {SendMailComponent} from "@app/shared/modals/send-mail/send-mail.component";
import {NgbModal} from "@ng-bootstrap/ng-bootstrap";

@Component({
    selector: "src-notification-tab1",
    templateUrl: "./notification-tab1.component.html",
    standalone: true,
    imports: [NgbNav, NgSelectComponent, NgOptionTemplateDirective, NgbNavItem, NgbNavItemRole, NgbNavLinkButton, NgbNavLinkBase, NgbNavContent, NgTemplateOutlet, NgbNavOutlet,FormsModule, NgbTooltipModule, TranslatorPipe]
})
export class NotificationTab1Component {
  protected nodeResolver = inject(NodeResolver);
  protected notificationResolver = inject(NotificationsResolver);
  private utilsService = inject(UtilsService);
  private modalService = inject(NgbModal);

  @Input() notificationForm: NgForm;
  protected readonly Constants = Constants;
  smtpTabActive = 'smtp1';
  selected = {value: []};
  supported_template_types = [
    'null',
    'tip',
    'tip_access',
    'tip_reminder',
    'tip_update',
    'tip_expiration_summary',
    'unread_tips',
    'pgp_alert',
    'admin_pgp_alert',
    'export_template',
    'export_comment',
    'admin_anomaly',
    'admin_test',
    'https_certificate_expiration',
    'https_certificate_renewal_failure',
    'software_update_available',
    'admin_signup_alert',
    'signup',
    'activation',
    'email_validation',
    'account_activation',
    'password_reset_validation',
    'user_credentials',
    'identity_access_request',
    'identity_access_authorized',
    'identity_access_denied'
  ]
  
  updateNotification(notification: notificationResolverModel) {
    this.utilsService.updateAdminNotification(notification).subscribe(_ => {
      this.utilsService.reloadComponent();
    });
  }

  updateThenTestMail(notification: notificationResolverModel,smtp2?: boolean): void {
    const modalRef = this.modalService.open(SendMailComponent, {backdrop: 'static', keyboard: false});
    modalRef.componentInstance.confirmFunction = (email: string) => {
      this.utilsService.updateAdminNotification(notification)
        .pipe(switchMap(() => this.utilsService.runAdminOperation("test_mail", smtp2 ? {smtp2 : smtp2, to_mail_address : email} : {to_mail_address : email}, true))).subscribe();
    };
  }

  selectTemplate(template: string) {
    if (template && (this.notificationResolver.dataModel.smtp2_template_types.indexOf(template) === -1)) {
      this.notificationResolver.dataModel.smtp2_template_types.push(template)
      this.notificationResolver.dataModel.smtp2_template_types.sort();
    }
    this.selected.value = [];
  }

  removeTemplate(index: number) {
    this.notificationResolver.dataModel.smtp2_template_types.splice(index, 1);
  }

  resetSMTPSettings(smtp2?: boolean) {
    this.utilsService.runAdminOperation("reset_smtp_settings", smtp2 ? {smtp2 : smtp2} : {}, true).subscribe();
  }

  resetTemplates() {
    this.utilsService.runAdminOperation("reset_templates", {}, true).subscribe();
  }
}
