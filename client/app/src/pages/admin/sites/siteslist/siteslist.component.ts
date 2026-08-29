import {Component, ElementRef, OnInit, inject, input, output} from "@angular/core";
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
export class SiteslistComponent implements OnInit {
  protected nodeResolver = inject(NodeResolver);
  protected appDataService = inject(AppDataService);
  private modalService = inject(NgbModal);
  private httpService = inject(HttpService);
  private utilsService = inject(UtilsService);
  private elementRef = inject(ElementRef);

  readonly tenant = input.required<tenantResolverModel>();
  readonly tenants = input<tenantResolverModel[]>();
  // The profiles of the platform, the sites are read by the one they use
  readonly profiles = input<tenantResolverModel[]>();
  readonly index = input<number>();
  // A link pointing at this site opens its card and brings it into view
  readonly expanded = input(false);
  readonly deleted = output<number>();
  editing = false;

  // The profile the site inherits from, named among the profiles
  protected get profileName(): string {
    const profile = (this.profiles() || []).find(entry => entry.uuid === this.tenant().profile);

    return profile ? profile.name : "";
  }

  ngOnInit(): void {
    if (this.expanded()) {
      this.editing = true;
      // The card is reached from elsewhere: it is brought into view once the
      // list holding it has been laid out
      setTimeout(() => this.elementRef.nativeElement.scrollIntoView({behavior: "smooth", block: "start"}));
    }
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

  // The confirmation states what the deletion carries away; if the statistics changed meanwhile the
  // deletion is refused
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
      // The dialog states what the deletion carries away and closes before it is performed: its
      // counts are read from the instance
      const dialog = modalRef.componentInstance;
      dialog.tenant = arg;
      dialog.statsChanged = statsChanged;

      dialog.confirmFunction = () => {
        const stats = dialog.tenantStats;
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
