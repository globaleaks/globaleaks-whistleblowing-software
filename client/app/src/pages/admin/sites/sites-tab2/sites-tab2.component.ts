import {Component, ElementRef, OnInit, ViewChild, inject} from "@angular/core";
import {tenantResolverModel} from "@app/models/resolvers/tenant-resolver-model";
import {HttpService} from "@app/shared/services/http.service";
import {FormsModule} from "@angular/forms";
import {SlicePipe} from "@angular/common";
import {NgbPagination, NgbPaginationPrevious, NgbPaginationNext, NgbPaginationFirst, NgbPaginationLast, NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {FilterPipe} from "@app/shared/pipes/filter.pipe";
import {OrderByPipe} from "@app/shared/pipes/order-by.pipe";
import {TranslateModule} from "@ngx-translate/core";
import {ProfilelistComponent} from "../profilelist/profilelist.component";
import {UtilsService} from "@app/shared/services/utils.service";
import {HttpClient} from "@angular/common/http";

@Component({
  selector: 'src-sites-tab3',
  templateUrl: './sites-tab3.component.html',
  standalone: true,
  imports: [FormsModule, ProfilelistComponent, NgbPagination, NgbPaginationPrevious, NgbPaginationNext, NgbPaginationFirst, NgbPaginationLast, NgbTooltipModule, SlicePipe, TranslatorPipe, FilterPipe, OrderByPipe, TranslateModule]
})
export class SitesTab3Component implements OnInit {
  private httpService = inject(HttpService);
  private utilsService = inject(UtilsService);
  private http = inject(HttpClient);
  @ViewChild('keyUploadInput') keyUploadInput: ElementRef<HTMLInputElement>;

  search: string;
  newTenant: { name: string, active: boolean, profile: string, mode: string, subdomain: string, is_profile: boolean} = {
    name: "",
    active: true,
    mode: "",
    profile: "default",
    subdomain: "",
    is_profile: true
  };
  tenants: tenantResolverModel[];
  showAddTenant: boolean = false;
  itemsPerPage: number = 10;
  currentPage: number = 1;
  indexNumber: number = 0;

  ngOnInit(): void {
    this.getResolver();
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

  getResolver(){
    this.httpService.fetchTenant().subscribe(
      tenants => {
        this.tenants = tenants.filter(tenant => tenant.id > 1000001);
      }
    );
  }

}
