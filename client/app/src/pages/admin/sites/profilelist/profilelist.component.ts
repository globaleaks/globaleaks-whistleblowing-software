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
import {DatePipe} from "@angular/common";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {TranslateModule} from "@ngx-translate/core";

@Component({
  selector: "src-profilelist",
  templateUrl: "./profilelist.component.html",
  standalone: true,
  imports: [FormsModule, DatePipe, TranslatorPipe, TranslateModule]
})
export class ProfilelistComponent {
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
    this.tenant.default_profile = "default";
    const url = "api/admin/tenants/" + this.tenant.id;
    this.httpService.requestUpdateTenant(url, this.tenant).subscribe((_) => {});
  }

  isRemovableTenant(): boolean {
    return this.tenant.id !== 1;
  }

  saveTenant() {
    const url = "api/admin/tenants/" + this.tenant.id;
    this.httpService.requestUpdateTenant(url, this.tenant).subscribe((_) => {});
  }

  deleteTenant(event: Event, tenant: tenantResolverModel) {
    event.stopPropagation();
    this.openConfirmableModalDialog(tenant, "").subscribe((_) => {});
  }

  configureTenant($event: Event, tid: number): void {
    $event.stopPropagation();

    this.httpService
      .requestTenantSwitch("api/auth/tenantauthswitch/" + tid)
      .subscribe((res) => {
        window.open(res.redirect);
      });
  }

  openConfirmableModalDialog(
    arg: tenantResolverModel,
    scope: any
  ): Observable<string> {
    scope = !scope ? this : scope;
    return new Observable((observer) => {
      const modalRef = this.modalService.open(DeleteConfirmationComponent, {
        backdrop: "static",
        keyboard: false,
      });
      modalRef.componentInstance.arg = arg;
      modalRef.componentInstance.scope = scope;
      modalRef.componentInstance.confirmFunction = () => {
        observer.complete();
        const url = "api/admin/tenants/" + arg.id;
        return this.httpService.requestDeleteTenant(url).subscribe((_) => {
          this.utilsService.deleteResource(this.tenants, arg);
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
