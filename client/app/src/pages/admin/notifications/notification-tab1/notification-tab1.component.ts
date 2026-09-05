import {Component, inject, input} from "@angular/core";
import {TranslatePipe} from "@ngx-translate/core";
import {NgForm, FormsModule} from "@angular/forms";
import {notificationResolverModel} from "@app/models/resolvers/notification-resolver-model";
import {NotificationsResolver} from "@app/shared/resolvers/notifications.resolver";
import {UtilsService} from "@app/shared/services/utils.service";

@Component({
    selector: "src-notification-tab1",
    templateUrl: "./notification-tab1.component.html",
    standalone: true,
    imports: [TranslatePipe, FormsModule]
})
export class NotificationTab1Component {
  protected notificationResolver = inject(NotificationsResolver);
  private readonly utilsService = inject(UtilsService);

  readonly notificationForm = input.required<NgForm>();

  updateNotification(notification: notificationResolverModel) {
    this.utilsService.updateAdminNotification(notification).subscribe();
  }
}
