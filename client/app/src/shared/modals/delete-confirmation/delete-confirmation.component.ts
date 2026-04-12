import {HttpClient} from "@angular/common/http";
import {Component, Input, OnInit, inject, signal} from "@angular/core";
import {NgbActiveModal} from "@ng-bootstrap/ng-bootstrap";
import {HttpService} from "@app/shared/services/http.service";
import {UtilsService} from "@app/shared/services/utils.service";
import {Router} from "@angular/router";
import {TranslateModule} from "@ngx-translate/core";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {User} from "@app/models/resolvers/user-resolver-model";
import {tenantResolverModel} from "@app/models/resolvers/tenant-resolver-model";
import {contextResolverModel} from "@app/models/resolvers/context-resolver-model";

@Component({
  selector: "src-delete-confirmation",
  templateUrl: "./delete-confirmation.component.html",
  standalone: true,
  imports: [TranslateModule, TranslatorPipe]
})
export class DeleteConfirmationComponent implements OnInit {

  private modalService = inject(NgbActiveModal);
  private http = inject(HttpClient);
  private httpService = inject(HttpService);
  private utils = inject(UtilsService);
  protected router = inject(Router);

  @Input() args: any;
  @Input() selected_tips: string[];
  @Input() operation: string;
  @Input() user: User;
  @Input() tenant: tenantResolverModel;
  @Input() context: contextResolverModel;
  @Input() statsChanged = false;

  confirmFunction: () => void;

  userStats: {total_reports: number; exclusive_reports: number; last_update: string} | null = null;
  tenantStats: {open_reports: number; total_reports: number; last_update: string} | null = null;

  loadingStats = signal(false);

  ngOnInit() {
    if (this.user) {
      this.loadUserStats();
    }
    if (this.tenant) {
      this.loadTenantStats();
    }
  }

  loadUserStats() {
    this.loadingStats.set(true);
    this.httpService.requestAdminUserStats(this.user.id).subscribe({
      next: (stats) => {
        this.userStats = stats;
        this.loadingStats.set(false);
      },
      error: () => {
        this.loadingStats.set(false);
      }
    });
  }

  loadTenantStats() {
    this.loadingStats.set(true);
    this.httpService.requestAdminTenantStats(this.tenant.id).subscribe({
      next: (stats) => {
        this.tenantStats = stats;
        this.loadingStats.set(false);
      },
      error: () => {
        this.loadingStats.set(false);
      }
    });
  }

  openAuditLog() {
    this.cancel();
    this.router.navigate(['/admin/auditlog'], {queryParams: {user: this.user.id}});
  }

  confirm() {
    this.proceedWithDeletion();
  }

  private proceedWithDeletion() {
    this.cancel();
    this.confirmFunction();
    if (this.args) {
      if (this.args.operation === "delete") {
        return this.http.delete("api/recipient/rtips/" + this.args.tip.id)
          .subscribe(() => {
            this.router.navigate(["/recipient/reports"]).then();
          });
      }
      return;
    }
    if (this.operation) {
      if (["delete"].indexOf(this.operation) === -1) {
        return;
      }
    }

    if (this.selected_tips) {
      return this.utils.runRecipientOperation(this.operation, {"rtips": this.selected_tips}, true).subscribe({
        next: _ => {
          this.utils.reloadCurrentRoute();
        }
      });
    } else {
      return null;
    }
  }

  cancel() {
    this.modalService.dismiss();
  }
}
