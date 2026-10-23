import {Component, OnInit, inject} from "@angular/core";
import {NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {tenantResolverModel} from "@app/models/resolvers/tenant-resolver-model";
import {HttpService} from "@app/shared/services/http.service";
import {FormsModule} from "@angular/forms";
import {TranslatePipe} from "@ngx-translate/core";
import {SiteslistComponent} from "../siteslist/siteslist.component";
import {PaginatedInterfaceComponent} from "@app/shared/components/paginated-interface/paginated-interface.component";


@Component({
    selector: "src-sites-tab1",
    templateUrl: "./sites-tab1.component.html",
    standalone: true,
    imports: [FormsModule, NgbTooltipModule, PaginatedInterfaceComponent, SiteslistComponent, TranslatePipe]
})
export class SitesTab1Component implements OnInit {
  private httpService = inject(HttpService);

  newTenant: { name: string, active: boolean, mode: string, subdomain: string } = {
    name: "",
    active: true,
    mode: "default",
    subdomain: ""
  };
  tenants: tenantResolverModel[] = [];
  showAddTenant = false;

  ngOnInit(): void {
    this.httpService.fetchTenant().subscribe(
      tenant => {
        this.tenants = tenant;
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
    });
  }

  onDelete(id: number) {
    this.tenants = this.tenants.filter(i => i.id !== id);
  }
}
