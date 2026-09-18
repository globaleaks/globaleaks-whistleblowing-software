import {CollapsibleCardComponent} from "@app/shared/components/collapsible-card/collapsible-card.component";
import {Component, EventEmitter, Input, Output, inject} from "@angular/core";
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
import {TranslateModule} from "@ngx-translate/core";
import {AuthenticationService} from "@app/services/helper/authentication.service";

@Component({
  selector: "src-profilelist",
  templateUrl: "./profilelist.component.html",
  standalone: true,
  imports: [CollapsibleCardComponent, CommonModule, FormsModule, DatePipe, TranslateModule]
})
export class ProfilelistComponent {
  protected nodeResolver = inject(NodeResolver);
  protected appDataService = inject(AppDataService);
  private readonly modalService = inject(NgbModal);
  private readonly httpService = inject(HttpService);
  private readonly utilsService = inject(UtilsService);
  private readonly authenticationService = inject(AuthenticationService);

  @Input() editTenant: NgForm;
  @Input() tenant: tenantResolverModel;
  @Input() tenants: tenantResolverModel[];
  @Input() index: number;
  @Input() indexNumber: number;
  @Output() deleted = new EventEmitter<number>();
  editing = false;

  isRemovableTenant(): boolean {
    return this.tenant.id !== 1;
  }

  saveTenant() {
    this.tenant.profile = 'default';
    const url = "api/admin/tenants/" + this.tenant.id;
    this.httpService.requestUpdateTenant(url, this.tenant).subscribe();
  }

  deleteTenant(event: Event, tenant: tenantResolverModel, statsChanged = false) {
    event.stopPropagation();
    this.openConfirmableModalDialog(tenant, statsChanged).subscribe();
  }

  exportTenant(tenant:tenantResolverModel){
    this.utilsService.saveAs(this.authenticationService, tenant.name + ".json", "api/admin/tenants/" + tenant.id);
  }

  configureTenant($event: Event, tid: number): void {
    $event.stopPropagation();

    this.httpService
      .requestTenantSwitch("api/auth/tenantauthswitch/" + tid)
      .subscribe((res) => {
        window.open(res.redirect);
      });
  }

  openConfirmableModalDialog(arg: tenantResolverModel, statsChanged = false): Observable<string> {
    return new Observable((observer) => {
      const modalRef = this.modalService.open(DeleteConfirmationComponent, {
        backdrop: "static",
        keyboard: false,
      });
      // The dialog states what the deletion carries away and closes before it is performed: its
      // counts are read from the instance
      const dialog = modalRef.componentInstance;
      dialog.tenant = arg;
      dialog.statsChanged = statsChanged;

      dialog.confirmFunction = () => {
        const stats = dialog.tenantStats;
        observer.complete();
        const url = "api/admin/tenants/" + arg.id;
        return this.utilsService.deleteWithConfirmation(url, stats).subscribe({
          next: () => {
            this.deleted.emit(arg.id);
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

  toggleEditing(): void {
    if (this.tenant.id !== 1) {
      this.editing = !this.editing;
    }
  }
}
