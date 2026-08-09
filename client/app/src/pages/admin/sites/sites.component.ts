import {Component, inject} from "@angular/core";
import {TabsComponent} from "@app/shared/components/tabs/tabs.component";
import {TabDirective} from "@app/shared/components/tabs/tab.directive";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {SitesTab1Component} from "@app/pages/admin/sites/sites-tab1/sites-tab1.component";
import {SitesTab2Component} from "@app/pages/admin/sites/sites-tab2/sites-tab2.component";
import {SitesTab3Component} from "@app/pages/admin/sites/sites-tab3/sites-tab3.component";
import {SitesTab4Component} from "@app/pages/admin/sites/sites-tab4/sites-tab4.component";
import {SitesTab5Component} from "@app/pages/admin/sites/sites-tab5/sites-tab5.component";

@Component({
    selector: "src-sites",
    templateUrl: "./sites.component.html",
    standalone: true,
    imports: [TabsComponent, TabDirective, SitesTab1Component, SitesTab2Component, SitesTab3Component, SitesTab4Component, SitesTab5Component]
})
export class SitesComponent {
  protected node = inject(NodeResolver);

  protected isAdmin = inject(AuthenticationService).session.role === "admin";

  // The registrations are offered only where the signup is open
  protected get areInvitesConfigurable(): boolean {
    return this.isAdmin && this.node.dataModel.enable_signup;
  }
}
