import {Component, Input, inject} from "@angular/core";
import {AppDataService} from "@app/app-data.service";
import {DeleteConfirmationComponent} from "@app/shared/modals/delete-confirmation/delete-confirmation.component";
import {NgbModal} from "@ng-bootstrap/ng-bootstrap";
import {HttpService} from "@app/shared/services/http.service";
import {UtilsService} from "@app/shared/services/utils.service";
import {NgForm, FormsModule} from "@angular/forms";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {tenantResolverModel} from "@app/models/resolvers/tenant-resolver-model";
import {Observable} from "rxjs";
import {CommonModule, DatePipe} from "@angular/common";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {TranslateModule} from "@ngx-translate/core";

@Component({
    selector: "src-siteslist",
    templateUrl: "./siteslist.component.html",
    standalone: true,
    imports: [CommonModule, FormsModule, DatePipe, TranslatorPipe, TranslateModule]
})
export class SiteslistComponent {
  protected nodeResolver = inject(NodeResolver);
  protected appDataService = inject(AppDataService);
  private modalService = inject(NgbModal);
  private httpService = inject(HttpService);
  private utilsService = inject(UtilsService);

  @Input() editTenant: NgForm;
  @Input() tenant: tenantResolverModel;
  @Input() tenants: tenantResolverModel[];
  @Input() index: number;
  @Input() indexNumber: number;
  editing = false;

  toggleActivation(event: Event): void {
    event.stopPropagation();
    this.tenant.active = !this.tenant.active;
    this.tenant.profile = "default";
    const url = "api/admin/tenants/" + this.tenant.id;
    this.httpService.requestUpdateTenant(url, this.tenant).subscribe(_ => {
    });
  }

  isRemovableTenant(): boolean {
    return this.tenant.id !== 1;
  }

  saveTenant() {
    this.tenant.profile = "default";
    const url = "api/admin/tenants/" + this.tenant.id;
    this.httpService.requestUpdateTenant(url, this.tenant).subscribe(_ => {
    });
  }

  deleteTenant(event: Event, tenant: tenantResolverModel, statsChanged = false) {
    event.stopPropagation();
    this.openConfirmableModalDialog(tenant, statsChanged).subscribe();
  }

  configureTenant($event: Event, tid: number): void {
    $event.stopPropagation();

    this.httpService.requestTenantSwitch("api/auth/tenantauthswitch/" + tid).subscribe(res => {
      window.open(res.redirect);
    });
  }

  openConfirmableModalDialog(arg: tenantResolverModel, statsChanged = false): Observable<string> {
    return new Observable((observer) => {
      const modalRef = this.modalService.open(DeleteConfirmationComponent, {backdrop: 'static', keyboard: false});
      modalRef.componentInstance.tenant = arg;
      modalRef.componentInstance.statsChanged = statsChanged;

      modalRef.componentInstance.confirmFunction = (stats: any) => {
        observer.complete();
        const url = "api/admin/tenants/" + arg.id;
        return this.httpService.requestDeleteTenant(url, stats || undefined).subscribe({
          next: () => {
          this.utilsService.deleteResource(this.tenants, arg);
          },
          error: (err) => {
            if (err.status === 409) {
              this.deleteTenant(new Event('click'), arg, true);
            }
          }
        });
      };
    });
  }

  toggleEditing(event: Event): void {
    event.stopPropagation();
    if (this.tenant.id !== 1) {
      this.editing = !this.editing;
    }
  }
}
