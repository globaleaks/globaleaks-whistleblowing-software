import {Component, OnInit, inject, signal, ChangeDetectionStrategy} from "@angular/core";
import {NgbActiveModal} from "@ng-bootstrap/ng-bootstrap";
import {UtilsService} from "@app/shared/services/utils.service";
import {HttpService} from "@app/shared/services/http.service";
import {Router} from "@angular/router";
import {TranslateModule} from "@ngx-translate/core";
import {User} from "@app/models/resolvers/user-resolver-model";
import {tenantResolverModel} from "@app/models/resolvers/tenant-resolver-model";
import {contextResolverModel} from "@app/models/resolvers/context-resolver-model";


@Component({
    changeDetection: ChangeDetectionStrategy.OnPush,
    selector: "src-delete-confirmation",
    templateUrl: "./delete-confirmation.component.html",
    standalone: true,
    imports: [TranslateModule]
})
export class DeleteConfirmationComponent implements OnInit {
  private modalService = inject(NgbActiveModal);
  private httpService = inject(HttpService);
  private utils = inject(UtilsService);
  protected router = inject(Router);


  args: any;
  selected_tips: string[];
  operation: string;
  user: User;
  tenant: tenantResolverModel;
  context: contextResolverModel;
  statsChanged = false;
  confirmFunction: () => void;

  userStats: {total_reports: number; exclusive_reports: number; last_update: string} | null = null;
  tenantStats: {open_reports: number; total_reports: number; last_update: string} | null = null;

  readonly loadingStats = signal(false);

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
    this.router.navigate(["/admin/auditlog"], {queryParams: {user: this.user.id}}).then();
  }

  confirm() {
    this.cancel();
    this.confirmFunction();
    const args = this.args;
    if (args) {
      if (args.operation === "delete") {
        return this.httpService.requestDeleteReceiverTip(args.tip.id)
          .subscribe(() => {
            this.router.navigate(["/recipient/reports"]).then();
          });
      }
      return;
    }
    const operation = this.operation;
    if (operation) {
      if (["delete"].indexOf(operation) === -1) {
        return;
      }
    }

    const selected_tips = this.selected_tips;
    if (selected_tips) {
      return this.utils.runRecipientOperation(operation, {"rtips": selected_tips}, true).subscribe({
        next: () => {
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
