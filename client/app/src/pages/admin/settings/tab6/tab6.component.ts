import {DatePipe} from "@angular/common";
import {Component, inject, input, OnInit} from "@angular/core";
import {FormsModule, NgForm} from "@angular/forms";
import {Backup} from "@app/models/admin/backup";
import {nodeResolverModel} from "@app/models/resolvers/node-resolver-model";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {HttpService} from "@app/shared/services/http.service";
import {UtilsService} from "@app/shared/services/utils.service";
import {TranslateModule} from "@ngx-translate/core";

@Component({
  selector: "src-tab6",
  templateUrl: "./tab6.component.html",
  standalone: true,
  imports: [FormsModule, DatePipe, TranslateModule]
})
export class Tab6Component implements OnInit {
  protected utilsService = inject(UtilsService);
  private readonly nodeResolver = inject(NodeResolver);
  private readonly httpService = inject(HttpService);

  readonly contentForm = input.required<NgForm>();

  nodeData: nodeResolverModel;
  backupEnabled = false;
  backupTime = "";
  backupPeriod: number;
  backupRetention: number;
  periodOptions: number[] = Array.from({length: 24}, (_, i) => i + 1);
  jobStatus = "";
  backups: Backup[] = [];

  ngOnInit(): void {
    this.nodeData = this.nodeResolver.dataModel;
    this.loadBackupInterval();
    this.loadBackups();
  }

  loadBackups(): void {
    this.httpService.requestBackupsResource().subscribe(backups => {
      // Newest first: the backend returns the generations oldest-first.
      this.backups = (backups || []).slice().reverse();
    });
  }

  loadBackupInterval() {
    this.backupEnabled = this.nodeData.backup_enabled;
    this.backupTime = this.formatBackupTime(this.nodeData.backup_time);
    this.backupPeriod = this.nodeData.backup_period;
    this.backupRetention = this.nodeData.backup_retention;
    this.jobStatus = this.nodeData.backup_job_status;
  }

  formatBackupTime(iso8601: string): string {
    const match = iso8601.match(/(?:T)?(\d{2}):(\d{2})/);
    return match ? `${match[1]}:${match[2]}` : "00:00";
  }

  save(): void {
    this.backupPeriod = Math.min(24, Math.max(1, Math.trunc(this.backupPeriod) || 1));
    this.nodeData.backup_enabled = this.backupEnabled;
    this.nodeData.backup_time = this.backupTime;
    this.nodeData.backup_period = this.backupPeriod;
    this.nodeData.backup_retention = this.backupRetention;
    this.utilsService.update(this.nodeResolver.dataModel).subscribe();
  }

  toggleBackup(): void {
    this.backupEnabled = !this.nodeData.backup_enabled;
    this.save();
  }

  resetBackups(): void {
    this.utilsService.deleteDialog("reset_backups");
  }
}
