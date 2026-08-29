import {Component, inject} from "@angular/core";
import {TabsComponent} from "@app/shared/components/tabs/tabs.component";
import {TabDirective} from "@app/shared/components/tabs/tab.directive";
import {FormsModule} from "@angular/forms";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {Tab1Component} from "@app/pages/admin/settings/tab1/tab1.component";
import {Tab2Component} from "@app/pages/admin/settings/tab2/tab2.component";
import {Tab3Component} from "@app/pages/admin/settings/tab3/tab3.component";
import {Tab4Component} from "@app/pages/admin/settings/tab4/tab4.component";
import {Tab6Component} from "@app/pages/admin/settings/tab6/tab6.component";
import {Tab7Component} from "@app/pages/admin/settings/tab7/tab7.component";
import {Tab8Component} from "@app/pages/admin/settings/tab8/tab8.component";

@Component({
    selector: "src-admin-settings",
    templateUrl: "./settings.component.html",
    standalone: true,
    imports: [TabsComponent, TabDirective, FormsModule, Tab1Component, Tab2Component, Tab3Component, Tab4Component, Tab6Component, Tab7Component, Tab8Component]
})
export class AdminSettingsComponent {
  private node = inject(NodeResolver);

  protected isAdmin = inject(AuthenticationService).session.role === "admin";

  // The antivirus and backup features are configurable on the primary tenant
  // only: their tabs are hidden on secondary tenants and profiles
  protected get isRootTenantAdmin(): boolean {
    return this.isAdmin && this.node.dataModel.root_tenant;
  }
}
