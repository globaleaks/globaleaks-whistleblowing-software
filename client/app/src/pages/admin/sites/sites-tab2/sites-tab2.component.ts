import {Component, ElementRef, OnInit, ViewChild, inject} from "@angular/core";
import {tenantResolverModel} from "@app/models/resolvers/tenant-resolver-model";
import {HttpService} from "@app/shared/services/http.service";
import {FormsModule} from "@angular/forms";
import {NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {TranslateModule} from "@ngx-translate/core";
import {PaginatedInterfaceComponent} from "@app/shared/components/paginated-interface/paginated-interface.component";
import {ProfilelistComponent} from "../profilelist/profilelist.component";
import {UtilsService} from "@app/shared/services/utils.service";
import {HttpClient} from "@angular/common/http";

@Component({
  selector: 'src-sites-tab2',
  templateUrl: './sites-tab2.component.html',
  standalone: true,
  imports: [FormsModule, PaginatedInterfaceComponent, ProfilelistComponent, NgbTooltipModule, TranslateModule]
})
export class SitesTab2Component implements OnInit {
  private httpService = inject(HttpService);
  private utilsService = inject(UtilsService);
  private http = inject(HttpClient);
  @ViewChild('keyUploadInput') keyUploadInput: ElementRef<HTMLInputElement>;

  newTenant: { name: string, active: boolean, profile: string, subdomain: string, is_profile: boolean} = {
    name: "",
    active: true,
    profile: "default",
    subdomain: "",
    is_profile: true
  };
  tenants: tenantResolverModel[] = [];
  showAddTenant: boolean = false;
  indexNumber: number = 0;

  ngOnInit(): void {
    this.getResolver();
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

  importTenant(files: FileList | null) {
    if (files && files.length > 0) {
      this.utilsService.readFileAsText(files[0]).subscribe((txt) => {
        let jsonTxt = JSON.parse(txt);
        jsonTxt.tenant.profile = "default";

        return this.http.post("api/admin/tenants", jsonTxt).subscribe({
          next: () => {
            this.getResolver();
          },
          error: () => {
            if (this.keyUploadInput) {
              this.keyUploadInput.nativeElement.value = "";
            }
          }
        });
      });
    }
  }

  onDelete(id: number) {
    this.tenants = this.tenants.filter(t => t.id !== id);
  }

  getResolver(){
    this.httpService.fetchTenant().subscribe(
      tenants => {
        this.tenants = tenants.filter(tenant => tenant.id > 1000001);
      }
    );
  }

}
