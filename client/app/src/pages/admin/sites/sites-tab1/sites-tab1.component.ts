import {Component, OnInit, inject} from "@angular/core";
import {NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {tenantResolverModel} from "@app/models/resolvers/tenant-resolver-model";
import {HttpService} from "@app/shared/services/http.service";
import {FormsModule} from "@angular/forms";
import {TranslateModule} from "@ngx-translate/core";
import {SiteslistComponent} from "../siteslist/siteslist.component";
import {PaginatedInterfaceComponent} from "@app/shared/components/paginated-interface/paginated-interface.component";


@Component({
    selector: "src-sites-tab1",
    templateUrl: "./sites-tab1.component.html",
    standalone: true,
    imports: [FormsModule, NgbTooltipModule, PaginatedInterfaceComponent, SiteslistComponent, TranslateModule]
})
export class SitesTab1Component implements OnInit {
  private httpService = inject(HttpService);

  newTenant: { name: string, active: boolean, profile: string, subdomain: string, is_profile: boolean} = {
    name: "",
    active: true,
    profile: "default",
    subdomain: "",
    is_profile: false
  };

  tenants: tenantResolverModel[] = [];
  siteProfiles: tenantResolverModel[] = [];
  showAddTenant = false;

  ngOnInit(): void {
    this.fetchTenants();
  }

  fetchTenants() {
    this.httpService.fetchTenant().subscribe(
      tenants => {
        this.tenants = tenants.filter(tenant => tenant.id < 1000001);
        this.siteProfiles = tenants.filter(tenant => tenant.id > 1000001);
      }
    );
  }

  toggleAddTenant() {
    this.showAddTenant = !this.showAddTenant;
  }

  addTenant() {
    this.httpService.addTenant(this.newTenant).subscribe(res => {
      this.tenants = [...this.tenants, res];
      this.newTenant.name = "";
      this.newTenant.profile = "default";
    });
  }

  onDelete(id: number) {
    this.tenants = this.tenants.filter(i => i.id !== id);
  }
}
