import {Component, OnInit, inject} from "@angular/core";
import {UtilsService} from "@app/shared/services/utils.service";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {FormsModule} from "@angular/forms";
import {tenantResolverModel} from "@app/models/resolvers/tenant-resolver-model";
import {HttpService} from "@app/shared/services/http.service";
import {SignupTosComponent} from "@app/pages/admin/sites/signup-tos/signup-tos.component";

import {TranslateModule} from "@ngx-translate/core";

@Component({
    selector: "src-sites-tab3",
    templateUrl: "./sites-tab3.component.html",
    standalone: true,
    imports: [FormsModule, SignupTosComponent, TranslateModule]
})
export class SitesTab3Component implements OnInit {
  protected nodeResolver = inject(NodeResolver);
  protected utilsService = inject(UtilsService);
  private readonly httpService = inject(HttpService);

  siteProfiles: tenantResolverModel[] = [];

  ngOnInit(): void {
    this.httpService.fetchTenant().subscribe(
      tenants => {
        this.siteProfiles = tenants.filter(tenant => tenant.id > 1000001);
      }
    );
  }
}
