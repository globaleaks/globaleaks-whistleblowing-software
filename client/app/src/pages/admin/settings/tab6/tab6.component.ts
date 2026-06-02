import {DatePipe} from "@angular/common";
import {HttpClient} from "@angular/common/http";
import {Component, inject, Input, OnInit} from "@angular/core";
import {FormsModule, NgForm} from "@angular/forms";
import {nodeResolverModel} from "@app/models/resolvers/node-resolver-model";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {UtilsService} from "@app/shared/services/utils.service";
import {TranslateModule} from "@ngx-translate/core";

@Component({
  selector: "src-tab6",
  templateUrl: "./tab6.component.html",
  standalone: true,
  imports: [FormsModule, DatePipe, TranslatorPipe, TranslateModule]
})
export class Tab6Component implements OnInit {
  @Input() contentForm: NgForm;
  nodeData: nodeResolverModel;
  backupEnabled: boolean = false;
  backupTime: string = '';
  backupPeriod: number;
  backupRetention: number;
  periodOptions: number[] = Array.from({length: 24}, (_, i) => i + 1);
  jobStatus: string = '';
  backups: { id: string; creation_date: string }[] = [];

  protected utilsService = inject(UtilsService);
  private nodeResolver = inject(NodeResolver);
  private http = inject(HttpClient);

  ngOnInit(): void {
    this.nodeData = this.nodeResolver.dataModel;
    this.loadBackupInterval();
    this.loadBackups();
  }
  loadBackups(): void {
    this.http.get<{ id: string; creation_date: string }[]>(`api/admin/backup/list`)
      .subscribe({
        next: (res) => {
          // Newest first: the backend returns the generations oldest-first.
          this.backups = (res || []).slice().reverse();
        }
      });
  }
  loadBackupInterval() {
    this.backupEnabled = this.nodeData.backup_enabled;
    this.backupTime = this.formatBackupTime(this.nodeData.backup_time);
    this.backupPeriod = this.nodeData.backup_period;
    this.backupRetention = this.nodeData.backup_retention;
    this.jobStatus = this.nodeData.backup_job_status
  }
  formatBackupTime(iso8601: string): string {
    const match = iso8601.match(/(?:T)?(\d{2}):(\d{2})/);
    return match ? `${match[1]}:${match[2]}` : '00:00';
  }


  save(): void {
    this.backupPeriod = Math.min(24, Math.max(1, Math.trunc(this.backupPeriod) || 1));
    this.nodeData.backup_enabled = this.backupEnabled;
    this.nodeData.backup_time = this.backupTime;
    this.nodeData.backup_period = this.backupPeriod;
    this.nodeData.backup_retention = this.backupRetention;
    this.utilsService.update(this.nodeResolver.dataModel).subscribe(_ => {})
  }

  toggleBackup(): void {
    this.backupEnabled = !this.nodeData.backup_enabled;
    this.save();
  }

  resetBackups(): void {
    this.utilsService.deleteDialog("reset_backups");
  }
}
