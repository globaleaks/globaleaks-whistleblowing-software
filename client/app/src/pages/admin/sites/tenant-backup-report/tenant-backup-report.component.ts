import {Component, inject} from "@angular/core";
import {NgbActiveModal} from "@ng-bootstrap/ng-bootstrap";
import {TranslatePipe} from "@ngx-translate/core";
import {TenantBackupInventory} from "@app/models/admin/tenant-backup";

@Component({
  selector: "src-tenant-backup-report",
  templateUrl: "./tenant-backup-report.component.html",
  standalone: true,
  imports: [TranslatePipe]
})
export class TenantBackupReportComponent {
  private readonly activeModal = inject(NgbActiveModal);

  inventory: TenantBackupInventory;

  close(): void {
    this.activeModal.close();
  }
}
