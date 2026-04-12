import {Component, Input, inject} from "@angular/core";
import {NgForm, FormsModule} from "@angular/forms";
import {notificationResolverModel} from "@app/models/resolvers/notification-resolver-model";
import {NotificationsResolver} from "@app/shared/resolvers/notifications.resolver";
import {UtilsService} from "@app/shared/services/utils.service";
import {switchMap} from "rxjs";
import {NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {NgTemplateOutlet} from "@angular/common";
import {NgSelectComponent, NgOptionTemplateDirective} from "@ng-select/ng-select";
import {SendMailComponent} from "@app/shared/modals/send-mail/send-mail.component";
import {NgbModal} from "@ng-bootstrap/ng-bootstrap";

@Component({
    selector: "src-notification-tab1",
    templateUrl: "./notification-tab1.component.html",
    standalone: true,
    imports: [FormsModule, NgbTooltipModule, TranslatorPipe]
})
export class NotificationTab1Component {
  private utilsService = inject(UtilsService);
  private modalService = inject(NgbModal);

  protected notificationResolver = inject(NotificationsResolver);

  @Input() notificationForm: NgForm;

  updateNotification(notification: notificationResolverModel) {
    this.utilsService.updateAdminNotification(notification).subscribe();
  }
}
