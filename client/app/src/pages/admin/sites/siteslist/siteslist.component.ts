import {Component, inject, input, output} from "@angular/core";
import {AppDataService} from "@app/app-data.service";
import {DeleteConfirmationComponent} from "@app/shared/modals/delete-confirmation/delete-confirmation.component";
import {NgbModal} from "@ng-bootstrap/ng-bootstrap";
import {HttpService} from "@app/shared/services/http.service";
import {UtilsService} from "@app/shared/services/utils.service";
import {FormsModule} from "@angular/forms";
import {ListItemComponent} from "@app/shared/components/list-item/list-item.component";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {tenantResolverModel} from "@app/models/resolvers/tenant-resolver-model";
import {Observable} from "rxjs";
import {DatePipe} from "@angular/common";
import {TranslateModule} from "@ngx-translate/core";

@Component({
    selector: "src-siteslist",
    templateUrl: "./siteslist.component.html",
    standalone: true,
    imports: [FormsModule, DatePipe, TranslateModule, ListItemComponent]
})
export class SiteslistComponent {
  protected nodeResolver = inject(NodeResolver);
  protected appDataService = inject(AppDataService);
  private modalService = inject(NgbModal);
  private httpService = inject(HttpService);
  private utilsService = inject(UtilsService);

  readonly tenant = input.required<tenantResolverModel>();
  readonly tenants = input<tenantResolverModel[]>();
  readonly index = input<number>();
  readonly deleted = output<number>();
  editing = false;

  toggleActivation(event: Event): void {
    event.stopPropagation();
    this.tenant().active = !this.tenant().active;

    const url = "api/admin/tenants/" + this.tenant().id;
    this.httpService.requestUpdateTenant(url, this.tenant()).subscribe();
  }

  isRemovableTenant(): boolean {
    return this.tenant().id !== 1;
  }

  saveTenant() {
    const url = "api/admin/tenants/" + this.tenant().id;
    this.httpService.requestUpdateTenant(url, this.tenant()).subscribe();
  }

  deleteTenant(tenant: tenantResolverModel) {
    this.openConfirmableModalDialog(tenant, "").subscribe();
  }

  configureTenant($event: Event, tid: number): void {
    $event.stopPropagation();

    this.httpService.requestTenantSwitch("api/auth/tenantauthswitch/" + tid).subscribe(res => {
      window.open(res.redirect, "_blank", "noopener");
    });
  }

  openConfirmableModalDialog(arg: tenantResolverModel, scope: any): Observable<string> {
    scope = !scope ? this : scope;
    return new Observable(() => {
      const modalRef = this.modalService.open(DeleteConfirmationComponent, {backdrop: 'static', keyboard: false});
      modalRef.componentInstance.arg = arg;
      modalRef.componentInstance.scope = scope;
      modalRef.componentInstance.confirmFunction = () => {
        return this.utilsService.deleteWithConfirmation("api/admin/tenants/" + arg.id).subscribe(() => {
          this.deleted.emit(this.tenant().id);
        });
      };
    });
  }

  viewTenant(tenant: tenantResolverModel) {
    window.open(`/t/${tenant.uuid}/#/`, "_blank", "noopener");
  }
}
