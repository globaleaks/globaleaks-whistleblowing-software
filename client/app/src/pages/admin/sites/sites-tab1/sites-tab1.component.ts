import {Component, OnInit, inject} from "@angular/core";
import {tenantResolverModel} from "@app/models/resolvers/tenant-resolver-model";
import {HttpService} from "@app/shared/services/http.service";
import {FormsModule} from "@angular/forms";
import {SlicePipe} from "@angular/common";
import {SiteslistComponent} from "../siteslist/siteslist.component";
import {NgbPagination, NgbPaginationPrevious, NgbPaginationNext, NgbPaginationFirst, NgbPaginationLast, NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {FilterPipe} from "@app/shared/pipes/filter.pipe";
import {FilterSearchPipe} from "@app/shared/pipes/filter-search.pipe";
import {OrderByPipe} from "@app/shared/pipes/order-by.pipe";
import {TranslateModule} from "@ngx-translate/core";

@Component({
    selector: "src-sites-tab1",
    templateUrl: "./sites-tab1.component.html",
    standalone: true,
    imports: [FormsModule, SiteslistComponent, NgbPagination, NgbPaginationPrevious, NgbPaginationNext, NgbPaginationFirst, NgbPaginationLast, NgbTooltipModule, SlicePipe, TranslatorPipe, FilterPipe, FilterSearchPipe, OrderByPipe, TranslateModule]
})
export class SitesTab1Component implements OnInit {
  private httpService = inject(HttpService);

  search: string;
  newTenant: { name: string, active: boolean, mode: string, subdomain: string } = {
    name: "",
    active: true,
    mode: "default",
    subdomain: ""
  };
  tenants: tenantResolverModel[];
  showAddTenant: boolean = false;
  itemsPerPage: number = 10;
  currentPage: number = 1;

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
      this.tenants.push(res);
      this.newTenant.name = "";
    });
  }
}
