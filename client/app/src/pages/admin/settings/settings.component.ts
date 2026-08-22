import {Component, inject} from "@angular/core";
import {TabsComponent} from "@app/shared/components/tabs/tabs.component";
import {TabDirective} from "@app/shared/components/tabs/tab.directive";
import {FormsModule} from "@angular/forms";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {Tab1Component} from "@app/pages/admin/settings/tab1/tab1.component";
import {Tab2Component} from "@app/pages/admin/settings/tab2/tab2.component";
import {Tab3Component} from "@app/pages/admin/settings/tab3/tab3.component";
import {Tab4Component} from "@app/pages/admin/settings/tab4/tab4.component";
import {Tab5Component} from "@app/pages/admin/settings/tab5/tab5.component";

@Component({
    selector: "src-admin-settings",
    templateUrl: "./settings.component.html",
    standalone: true,
    imports: [TabsComponent, TabDirective, FormsModule, Tab1Component, Tab2Component, Tab3Component, Tab4Component, Tab5Component]
})
export class AdminSettingsComponent {
  protected isAdmin = inject(AuthenticationService).session.role === "admin";
}
