import {HttpClient} from "@angular/common/http";
import {Component, Input, OnInit, inject} from "@angular/core";
import {NgbActiveModal} from "@ng-bootstrap/ng-bootstrap";
import {HttpService} from "@app/shared/services/http.service";
import {UtilsService} from "@app/shared/services/utils.service";
import {Router} from "@angular/router";
import {TranslateModule} from "@ngx-translate/core";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {User} from "@app/models/resolvers/user-resolver-model";
import {tenantResolverModel} from "@app/models/resolvers/tenant-resolver-model";


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
  @Input() statsChanged = false;
  confirmFunction: () => void;

  userStats: {total_reports: number; exclusive_reports: number; last_update: string | null} | null = null;
  tenantStats: {open_reports: number; total_reports: number; last_update: string | null} | null = null;
  loadingStats = false;

  ngOnInit() {
    if (this.user) {
      this.loadUserStats();
    }
    if (this.tenant) {
      this.loadTenantStats();
    }
  }

  loadUserStats() {
    this.loadingStats = true;
    this.httpService.requestAdminUserStats(this.user.id).subscribe({
      next: (stats) => {
        this.userStats = stats;
        this.loadingStats = false;
      },
      error: () => {
        this.loadingStats = false;
      }
    });
  }

  loadTenantStats() {
    this.loadingStats = true;
    this.httpService.requestAdminTenantStats(this.tenant.id).subscribe({
      next: (stats) => {
        this.tenantStats = stats;
        this.loadingStats = false;
      },
      error: () => {
        this.loadingStats = false;
      }
    });
  }

  openAuditLog() {
    this.cancel();
    this.router.navigate(['/admin/auditlog'], {queryParams: {user: this.user.id}});
  }

  confirm() {
    // For user deletion, verify stats haven't changed
    if (this.user && this.userStats) {
      this.loadingStats = true;
      this.httpService.requestAdminUserStats(this.user.id).subscribe({
        next: (freshStats) => {
          this.loadingStats = false;
          const statsChanged = (
            freshStats.total_reports !== this.userStats!.total_reports ||
            freshStats.exclusive_reports !== this.userStats!.exclusive_reports ||
            freshStats.last_update !== this.userStats!.last_update
          );
          if (statsChanged) {
            this.userStats = freshStats;
            this.statsChanged = true;
          } else {
            this.statsChanged = false;
            this.proceedWithDeletion();
          }
        },
        error: () => {
          this.loadingStats = false;
          this.proceedWithDeletion();
        }
      });
      return;
    }

    // For tenant deletion, verify stats haven't changed
    if (this.tenant && this.tenantStats) {
      this.loadingStats = true;
      this.httpService.requestAdminTenantStats(this.tenant.id).subscribe({
        next: (freshStats) => {
          this.loadingStats = false;
          const statsChanged = (
            freshStats.open_reports !== this.tenantStats!.open_reports ||
            freshStats.total_reports !== this.tenantStats!.total_reports ||
            freshStats.last_update !== this.tenantStats!.last_update
          );
          if (statsChanged) {
            this.tenantStats = freshStats;
            this.statsChanged = true;
          } else {
            this.statsChanged = false;
            this.proceedWithDeletion();
          }
        },
        error: () => {
          this.loadingStats = false;
          this.proceedWithDeletion();
        }
      });
      return;
    }

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
