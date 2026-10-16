import {Component, inject} from "@angular/core";
import {NgForm, FormsModule} from "@angular/forms";
import {smtpResolverModel} from "@app/models/resolvers/notification-resolver-model";
import {Constants} from "@app/shared/constants/constants";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {SMTP1Resolver, SMTP2Resolver} from "@app/shared/resolvers/notifications.resolver";
import {ResourceResolver} from "@app/shared/resolvers/resource-resolver";
import {UtilsService} from "@app/shared/services/utils.service";
import {NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {TranslatePipe} from "@ngx-translate/core";
import {SendMailComponent} from "@app/shared/modals/send-mail/send-mail.component";
import {NgbModal} from "@ng-bootstrap/ng-bootstrap";
import {NgSelectComponent, NgOptionTemplateDirective} from "@ng-select/ng-select";
import {HeldByProfileDirective} from "@app/shared/directive/held-by-profile.directive";
import {CollapsibleCardComponent} from "@app/shared/components/collapsible-card/collapsible-card.component";

type SMTPName = "smtp1" | "smtp2";

/**
 * The two servers the mails are sent through, each saved, tested and reset on its own
 *
 * A test goes through what the server holds: it is offered once the changes of its card are saved.
 */
@Component({
    selector: "src-notification-tab3",
    templateUrl: "./notification-tab3.component.html",
    standalone: true,
    imports: [CollapsibleCardComponent, HeldByProfileDirective, FormsModule, NgbTooltipModule, TranslatePipe, NgSelectComponent, NgOptionTemplateDirective]
})
export class NotificationTab3Component {
  protected readonly smtp1Resolver = inject(SMTP1Resolver);
  protected readonly smtp2Resolver = inject(SMTP2Resolver);
  private readonly nodeResolver = inject(NodeResolver);
  private readonly utilsService = inject(UtilsService);
  private readonly modalService = inject(NgbModal);

  protected readonly Constants = Constants;
  selected = {value: []};
  smtp1Expanded = false;
  smtp2Expanded = false;
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

  private resolver(name: SMTPName): ResourceResolver<smtpResolverModel> {
    return name === "smtp1" ? this.smtp1Resolver : this.smtp2Resolver;
  }

  // The server answers with the server alone, which does not say what the site holds: the node
  // is asked again, so that the command to give a value up is there as soon as the save has
  // created one
  private settle(name: SMTPName, form: NgForm, smtp: smtpResolverModel): void {
    this.resolver(name).dataModel = {...smtp, password: ""};
    form.form.markAsPristine();
    this.nodeResolver.reload();
  }

  saveSMTP(name: SMTPName, form: NgForm): void {
    this.utilsService.updateAdminSMTP(name, this.resolver(name).dataModel)
      .subscribe((smtp) => this.settle(name, form, smtp));
  }

  resetSMTP(name: SMTPName, form: NgForm): void {
    this.utilsService.resetAdminSMTP(name)
      .subscribe((smtp) => this.settle(name, form, smtp));
  }

  testSMTP(name: SMTPName): void {
    const modalRef = this.modalService.open(SendMailComponent, {backdrop: 'static', keyboard: false});
    modalRef.componentInstance.confirmFunction = (email: string) => {
      const args = name === "smtp2" ? {smtp2: true, to_mail_address: email} : {to_mail_address: email};
      this.utilsService.runAdminOperation("test_mail", args, false).subscribe();
    };
  }

  // The notifications sent through the secondary server are a variable as any other: a site
  // naming a profile reads the ones the profile chose and does not change them
  heldByProfile(key: string): boolean {
    return this.nodeResolver.heldByProfile(key);
  }

  selectTemplate(template: string, form: NgForm) {
    const types = this.smtp2Resolver.dataModel.template_types;

    if (template && (types.indexOf(template) === -1)) {
      types.push(template)
      types.sort();
      form.form.markAsDirty();
    }
    this.selected.value = [];
  }

  removeTemplate(index: number, form: NgForm) {
    this.smtp2Resolver.dataModel.template_types.splice(index, 1);
    form.form.markAsDirty();
  }
}
