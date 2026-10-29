import {Component, ElementRef, OnInit, inject, input, output} from "@angular/core";
import {HttpHeaders} from "@angular/common/http";
import {AppDataService} from "@app/app-data.service";
import {ConfirmationComponent} from "@app/shared/modals/confirmation/confirmation.component";
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
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {TenantBackupReportComponent} from "../tenant-backup-report/tenant-backup-report.component";
import {TranslatePipe} from "@ngx-translate/core";

@Component({
    selector: "src-siteslist",
    templateUrl: "./siteslist.component.html",
    standalone: true,
    imports: [FormsModule, DatePipe, TranslatePipe, ListItemComponent]
})
export class SiteslistComponent implements OnInit {
  protected nodeResolver = inject(NodeResolver);
  protected appDataService = inject(AppDataService);
  private readonly modalService = inject(NgbModal);
  private readonly httpService = inject(HttpService);
  private readonly utilsService = inject(UtilsService);
  private readonly elementRef = inject(ElementRef);
  private readonly authenticationService = inject(AuthenticationService);

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

    const url = "api/admin/tenants/" + this.tenant().id;
    this.httpService.requestUpdateTenant(url, this.updateRequest()).subscribe();
  }

  backupTenant(event: Event): void {
    event.stopPropagation();
    this.utilsService.saveAs(
      this.authenticationService,
      this.tenant().name + "-backup.tar.gz",
      "api/admin/tenants/" + this.tenant().id + "/backup"
    );
  }

  showBackupReport(event: Event): void {
    event.stopPropagation();
    this.httpService.requestTenantBackupReport(this.tenant().id).subscribe(response => {
      const modalRef = this.modalService.open(TenantBackupReportComponent, {
        backdrop: "static",
        keyboard: false,
        size: "xl",
        ariaLabelledBy: "tenant-backup-report-title"
      });
      modalRef.componentInstance.inventory = response;
    });
  }

  isRemovableTenant(): boolean {
    return this.tenant().id !== 1;
  }

  saveTenant() {
    const url = "api/admin/tenants/" + this.tenant().id;
    this.httpService.requestUpdateTenant(url, this.updateRequest()).subscribe();
  }

  // The update does not move a site between profiles, and the backend ignores the field: the
  // request carries it only because it is validated, and the site keeps showing the one it uses
  private updateRequest(): tenantResolverModel {
    return {...this.tenant(), profile: this.tenant().profile || "default"};
  }

  // The confirmation states what the deletion carries away; if the statistics changed meanwhile the
  // deletion is refused
  deleteTenant(tenant: tenantResolverModel, statsChanged = false) {
    this.openConfirmableModalDialog(tenant, statsChanged).subscribe();
  }

  /**
   * Free the site from the profile it names
   *
   * What the profile handed it becomes its own, and nothing changes for whoever looks at the
   * site. It goes one way alone, and the exchanges addressed to the profile no longer reach it:
   * as the deletion of a site, it is asked first and then with the credentials of whoever does it.
   */
  detachFromProfile($event: Event): void {
    $event.stopPropagation();

    const modalRef = this.modalService.open(ConfirmationComponent, {backdrop: "static", keyboard: false, ariaLabelledBy: "modal-title"});
    modalRef.componentInstance.confirmFunction = () => {
      this.utilsService.getConfirmation((secret: string) => {
        const headers = new HttpHeaders({"X-Confirmation": this.utilsService.encodeString(secret)});
        return this.httpService.requestDetachTenant(this.tenant().id, headers);
      }).subscribe(() => {
        this.tenant().profile = "default";
        this.utilsService.reloadComponent();
      });
    };
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
