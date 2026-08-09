import {Component, inject} from "@angular/core";
import {TabsComponent} from "@app/shared/components/tabs/tabs.component";
import {TabDirective} from "@app/shared/components/tabs/tab.directive";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {SitesTab1Component} from "@app/pages/admin/sites/sites-tab1/sites-tab1.component";
import {SitesTab2Component} from "@app/pages/admin/sites/sites-tab2/sites-tab2.component";
import {SitesTab5Component} from "@app/pages/admin/sites/sites-tab5/sites-tab5.component";

@Component({
    selector: "src-sites",
    templateUrl: "./sites.component.html",
    standalone: true,
    imports: [TabsComponent, TabDirective, SitesTab1Component, SitesTab2Component, SitesTab5Component]
})
export class SitesComponent {
  protected isAdmin = inject(AuthenticationService).session.role === "admin";
}
