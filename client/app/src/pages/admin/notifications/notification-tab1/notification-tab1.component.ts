import {Component, Input} from "@angular/core";
import {NgForm} from "@angular/forms";
import {notificationResolverModel} from "@app/models/resolvers/notification-resolver-model";
import {Constants} from "@app/shared/constants/constants";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {NotificationsResolver} from "@app/shared/resolvers/notifications.resolver";
import {UtilsService} from "@app/shared/services/utils.service";
import {switchMap} from "rxjs";

@Component({
  selector: "src-notification-tab1",
  templateUrl: "./notification-tab1.component.html"
})
export class NotificationTab1Component {
  @Input() notificationForm: NgForm;
  protected readonly Constants = Constants;

  collapsed = false;

  constructor(protected nodeResolver: NodeResolver, protected notificationResolver: NotificationsResolver, protected utilsService: UtilsService) {
  }

  public toggleCollapse() {
    this.collapsed = !this.collapsed;
  }

  updateNotification(notification: notificationResolverModel) {
    this.utilsService.updateAdminNotification(notification).subscribe(_ => {
      this.utilsService.reloadComponent();
    });
  }

  updateThenTestMail(notification: notificationResolverModel): void {
    this.utilsService
      .updateAdminNotification(notification)
      .pipe(
        switchMap(() => this.utilsService.runAdminOperation("test_mail", {}, true))
      )
      .subscribe();
  }

  resetSMTPSettings() {
    this.utilsService.runAdminOperation("reset_smtp_settings", {}, true).subscribe();
  }

  resetTemplates() {
    this.utilsService.runAdminOperation("reset_templates", {}, true).subscribe();
  }
}
