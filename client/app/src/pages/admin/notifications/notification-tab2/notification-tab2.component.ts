import {Component, computed, inject, input} from "@angular/core";
import {TranslatePipe} from "@ngx-translate/core";
import {NgForm, FormsModule} from "@angular/forms";
import {notificationResolverModel} from "@app/models/resolvers/notification-resolver-model";
import {NotificationsResolver} from "@app/shared/resolvers/notifications.resolver";
import {UtilsService} from "@app/shared/services/utils.service";


@Component({
    selector: "src-notification-tab2",
    templateUrl: "./notification-tab2.component.html",
    standalone: true,
    imports: [TranslatePipe, FormsModule]
})
export class NotificationTab2Component {
  private notificationResolver = inject(NotificationsResolver);
  private utilsService = inject(UtilsService);

  readonly notificationForm = input.required<NgForm>();
  template: string;
  protected readonly notificationData = computed(() => this.notificationResolver.resource.value());

  updateNotification(notification: notificationResolverModel) {
    this.utilsService.updateAdminNotification(notification).subscribe();
  }
}