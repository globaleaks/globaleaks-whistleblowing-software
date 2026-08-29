import {Component, inject, input} from "@angular/core";
import {NgForm, FormsModule} from "@angular/forms";
import {notificationResolverModel} from "@app/models/resolvers/notification-resolver-model";
import {Constants} from "@app/shared/constants/constants";
import {NotificationsResolver} from "@app/shared/resolvers/notifications.resolver";
import {UtilsService} from "@app/shared/services/utils.service";
import {switchMap} from "rxjs";
import {NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {TranslatePipe} from "@ngx-translate/core";
import {SendMailComponent} from "@app/shared/modals/send-mail/send-mail.component";
import {NgbModal} from "@ng-bootstrap/ng-bootstrap";
import {NgSelectComponent, NgOptionTemplateDirective} from "@ng-select/ng-select";

@Component({
    selector: "src-notification-tab3",
    templateUrl: "./notification-tab3.component.html",
    standalone: true,
    imports: [FormsModule, NgbTooltipModule, TranslatePipe, NgSelectComponent, NgOptionTemplateDirective]
})
export class NotificationTab3Component {
  protected notificationResolver = inject(NotificationsResolver);
  private readonly utilsService = inject(UtilsService);
  private readonly modalService = inject(NgbModal);

  readonly notificationForm = input.required<NgForm>();
  protected readonly Constants = Constants;
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
    'signup_invite',
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
    this.utilsService.updateAdminNotification(notification).subscribe();
  }

  updateThenTestMail(notification: notificationResolverModel,smtp2?: boolean): void {
    const modalRef = this.modalService.open(SendMailComponent, {backdrop: 'static', keyboard: false});
    modalRef.componentInstance.confirmFunction = (email: string) => {
      this.utilsService.updateAdminNotification(notification)
        .pipe(switchMap(() => this.utilsService.runAdminOperation("test_mail", smtp2 ? {smtp2 : smtp2, to_mail_address : email} : {to_mail_address : email}, false))).subscribe();
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
    const data = this.notificationResolver.dataModel;

    if (smtp2) {
      data.smtp2_server = 'mail.globaleaks.org';
      data.smtp2_port = 587;
      data.smtp2_username = 'globaleaks';
      data.smtp2_password = 'globaleaks';
      data.smtp2_source_email = 'notifications@globaleaks.org';
      data.smtp2_security = 'TLS';
      data.smtp2_authentication = true;
    } else {
      data.smtp_server = 'mail.globaleaks.org';
      data.smtp_port = 587;
      data.smtp_username = 'globaleaks';
      data.smtp_password = 'globaleaks';
      data.smtp_source_email = 'notifications@globaleaks.org';
      data.smtp_security = 'TLS';
      data.smtp_authentication = true;
    }
  }
}
