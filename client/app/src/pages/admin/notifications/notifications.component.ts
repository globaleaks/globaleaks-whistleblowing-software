import {Component, TemplateRef, ViewChild, AfterViewInit, ChangeDetectorRef, inject} from "@angular/core";
import {Tab} from "@app/models/component-model/tab";
import {NotificationTab1Component} from "@app/pages/admin/notifications/notification-tab1/notification-tab1.component";
import {NotificationTab2Component} from "@app/pages/admin/notifications/notification-tab2/notification-tab2.component";
import {NotificationTab3Component} from "@app/pages/admin/notifications/notification-tab3/notification-tab3.component";
import {FormsModule} from "@angular/forms";
import {NgbNav, NgbNavItem, NgbNavItemRole, NgbNavLinkButton, NgbNavLinkBase, NgbNavContent, NgbNavOutlet} from "@ng-bootstrap/ng-bootstrap";
import {NgTemplateOutlet} from "@angular/common";
import {TranslatorPipe} from "@app/shared/pipes/translate";

@Component({
    selector: "src-notifications",
    templateUrl: "./notifications.component.html",
    standalone: true,
    imports: [FormsModule, NgbNav, NgbNavItem, NgbNavItemRole, NgbNavLinkButton, NgbNavLinkBase, NgbNavContent, NgTemplateOutlet, NgbNavOutlet, NotificationTab1Component, NotificationTab2Component, NotificationTab3Component, TranslatorPipe]
})
export class NotificationsComponent implements AfterViewInit {
  private cdr = inject(ChangeDetectorRef);

  @ViewChild("tab1") tab1!: TemplateRef<NotificationTab1Component>;
  @ViewChild("tab2") tab2!: TemplateRef<NotificationTab2Component>;
  @ViewChild("tab3") tab3!: TemplateRef<NotificationTab3Component>;

  tabs: Tab[];
  active: string;

  ngAfterViewInit(): void {
    setTimeout(() => {
      this.active = "Notifications";

      this.tabs = [
        {
          id: "notifications",
          title: "Notifications",
          component: this.tab1
        },
        {
          id: "templates",
          title: "Templates",
          component: this.tab2
        },
        {
          id: "smtp",
          title: "SMTP",
          component: this.tab3
        }
      ];

      this.cdr.detectChanges();
    });
  }

}
