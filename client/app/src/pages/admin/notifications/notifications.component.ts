import {Component} from "@angular/core";
import {TabsComponent} from "@app/shared/components/tabs/tabs.component";
import {TabDirective} from "@app/shared/components/tabs/tab.directive";
import {FormsModule} from "@angular/forms";
import {NotificationTab1Component} from "@app/pages/admin/notifications/notification-tab1/notification-tab1.component";
import {NotificationTab2Component} from "@app/pages/admin/notifications/notification-tab2/notification-tab2.component";
import {NotificationTab3Component} from "@app/pages/admin/notifications/notification-tab3/notification-tab3.component";

@Component({
    selector: "src-notifications",
    templateUrl: "./notifications.component.html",
    standalone: true,
    imports: [TabsComponent, TabDirective, FormsModule, NotificationTab1Component, NotificationTab2Component, NotificationTab3Component]
})
export class NotificationsComponent {}
