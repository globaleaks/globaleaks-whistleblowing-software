import {Component, ElementRef, OnInit, ViewChild, inject} from "@angular/core";
import {ActivatedRoute} from "@angular/router";
import {NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {tenantResolverModel} from "@app/models/resolvers/tenant-resolver-model";
import {HttpService} from "@app/shared/services/http.service";
import {FormsModule} from "@angular/forms";
import {UtilsService} from "@app/shared/services/utils.service";
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
  private readonly httpService = inject(HttpService);
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly utilsService = inject(UtilsService);
  @ViewChild("tenantBackupInput") tenantBackupInput: ElementRef<HTMLInputElement>;

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

  // A link may point at one site: opened with its card expanded
  focusTenantId = "";
  private requestedTenant = "";

  ngOnInit(): void {
    this.fetchTenants();

    this.activatedRoute.queryParams.subscribe(params => {
      this.requestedTenant = params["id"] || "";
      this.resolveFocusTenant();
    });
  }

  fetchTenants() {
    this.httpService.fetchTenant().subscribe(
      tenants => {
        this.tenants = tenants.filter(tenant => tenant.id < 1000001);
        this.siteProfiles = tenants.filter(tenant => tenant.id > 1000001);
        this.resolveFocusTenant();
      }
    );
  }

  isFocused(tenant: tenantResolverModel): boolean {
    return this.focusTenantId !== "" && String(tenant.id) === this.focusTenantId;
  }

  private resolveFocusTenant() {
    const tenant = this.tenants.find(item => String(item.id) === this.requestedTenant || item.uuid === this.requestedTenant);
    this.focusTenantId = tenant ? String(tenant.id) : "";
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

  restoreTenant(files: FileList | null) {
    const file = files?.item(0);
    if (!file) {
      return;
    }

    const flow = this.utilsService.getFlowInstance();
    flow.opts.target = "api/admin/tenants/backup/import";
    flow.opts.singleFile = true;
    flow.on("fileSuccess", () => {
      this.tenantBackupInput.nativeElement.value = "";
      this.fetchTenants();
    });
    flow.on("fileError", () => {
      this.tenantBackupInput.nativeElement.value = "";
    });
    this.utilsService.onFlowUpload(flow, file);
  }

  onDelete(id: number) {
    this.tenants = this.tenants.filter(i => i.id !== id);
  }
}
