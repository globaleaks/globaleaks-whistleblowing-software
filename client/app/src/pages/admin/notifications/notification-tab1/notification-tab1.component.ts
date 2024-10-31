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

@Component({
    selector: "src-notification-tab1",
    templateUrl: "./notification-tab1.component.html",
    standalone: true,
    imports: [FormsModule, NgbTooltipModule, TranslatorPipe]
})
export class NotificationTab1Component {
  protected nodeResolver = inject(NodeResolver);
  protected notificationResolver = inject(NotificationsResolver);
  private utilsService = inject(UtilsService);

  @Input() notificationForm: NgForm;
  protected readonly Constants = Constants;

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
