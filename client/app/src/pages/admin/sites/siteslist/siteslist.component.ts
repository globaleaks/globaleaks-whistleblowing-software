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
  // The profiles of the platform, the sites are read by the one they use
  readonly profiles = input<tenantResolverModel[]>();
  readonly index = input<number>();
  readonly deleted = output<number>();
  editing = false;

  // The profile a site inherits its configuration from, named as it is named
  // among the profiles: a site is read by what it is made of, as an account is
  // read by the profile it holds
  protected get profileName(): string {
    const profile = (this.profiles() || []).find(entry => entry.uuid === this.tenant().profile);

    return profile ? profile.name : "";
  }

  toggleActivation(event: Event): void {
    event.stopPropagation();
    this.tenant().active = !this.tenant().active;
    this.tenant().profile = "default";

    const url = "api/admin/tenants/" + this.tenant().id;
    this.httpService.requestUpdateTenant(url, this.tenant()).subscribe();
  }

  isRemovableTenant(): boolean {
    return this.tenant().id !== 1;
  }

  saveTenant() {
    this.tenant().profile = "default";

    const url = "api/admin/tenants/" + this.tenant().id;
    this.httpService.requestUpdateTenant(url, this.tenant()).subscribe();
  }

  // The confirmation states what the deletion carries away: the dialog asks
  // the statistics of the site and, if they changed while it was open, the
  // backend rejects the deletion and the dialog is presented once again
  deleteTenant(tenant: tenantResolverModel, statsChanged = false) {
    this.openConfirmableModalDialog(tenant, statsChanged).subscribe();
  }

  configureTenant($event: Event, tid: number): void {
    $event.stopPropagation();

    this.httpService.requestTenantSwitch("api/auth/tenantauthswitch/" + tid).subscribe(res => {
      window.open(res.redirect, "_blank", "noopener");
    });
  }

  openConfirmableModalDialog(arg: tenantResolverModel, statsChanged = false): Observable<string> {
    return new Observable((observer) => {
      const modalRef = this.modalService.open(DeleteConfirmationComponent, {backdrop: 'static', keyboard: false});
      modalRef.componentInstance.tenant = arg;
      modalRef.componentInstance.statsChanged = statsChanged;

      modalRef.componentInstance.confirmFunction = () => {
        const stats = modalRef.componentInstance.tenantStats;
        observer.complete();

        return this.utilsService.deleteWithConfirmation("api/admin/tenants/" + arg.id, stats).subscribe({
          next: () => {
            this.deleted.emit(this.tenant().id);
          },
          error: (err) => {
            if (err.status === 409) {
              this.deleteTenant(arg, true);
            }
          }
        });
      };
    });
  }

  viewTenant(tenant: tenantResolverModel) {
    window.open(`/t/${tenant.uuid}/#/`, "_blank", "noopener");
  }
}
