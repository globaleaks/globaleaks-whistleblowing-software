import {Component} from "@angular/core";
import {TabsComponent} from "@app/shared/components/tabs/tabs.component";
import {TabDirective} from "@app/shared/components/tabs/tab.directive";
import {SupportTab1Component} from "@app/pages/admin/support/support-tab1/support-tab1.component";

@Component({
    selector: "src-admin-support",
    templateUrl: "./support.component.html",
    standalone: true,
    imports: [TabsComponent, TabDirective, SupportTab1Component]
})
export class AdminSupportComponent {}
