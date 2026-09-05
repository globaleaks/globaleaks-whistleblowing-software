import {Component, Input, inject, OnInit, ChangeDetectorRef} from "@angular/core";
import {NgbActiveModal} from "@ng-bootstrap/ng-bootstrap";
import {DatePipe, NgTemplateOutlet} from "@angular/common";
import {TranslateModule, TranslateService} from "@ngx-translate/core";
import {PaginatedInterfaceComponent} from "@app/shared/components/paginated-interface/paginated-interface.component";
import {TableHeaderComponent} from "@app/shared/components/table/table-header.component";
import {TableFilterOption, TableState} from "@app/shared/components/table/table-state";
import {HttpService} from "@app/shared/services/http.service";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {UtilsService} from "@app/shared/services/utils.service";
import {auditlogResolverModel} from "@app/models/resolvers/auditlog-resolver-model";

interface AuditLogEntry {
  id: string;
  user: string;
  action: string;
  type: string;
  timestamp: Date;
  data?: any;
  // What a deletion leaves of the content it took away
  hash_sha256?: string;
  hash_sha512?: string;
}

interface GroupedAuditLogEntry extends AuditLogEntry {
  isGroup?: boolean;
  groupedEntries?: AuditLogEntry[];
  groupCount?: number;
}

@Component({
  selector: "src-tip-audit-log",
  templateUrl: "./tip-audit-log.component.html",
  standalone: true,
  imports: [DatePipe, NgTemplateOutlet, PaginatedInterfaceComponent, TableHeaderComponent, TranslateModule],
  styles: [`
    .table {
      table-layout: fixed;
    }

    .audit-detail-line {
      font-size: 0.8125rem;
    }

    .audit-detail-line + .audit-detail-line {
      margin-top: 0.5em;
    }

    .audit-detail-line code {
      word-break: break-all;
    }
  `]
})

export class TipAuditLogComponent implements OnInit {
  private readonly activeModal = inject(NgbActiveModal);
  private readonly translateService = inject(TranslateService);
  private readonly httpService = inject(HttpService);
  private readonly authenticationService = inject(AuthenticationService);
  private readonly utilsService = inject(UtilsService);
  private readonly cdr = inject(ChangeDetectorRef);

  @Input() tipId = '';
  @Input() tipData: any = null; // Will receive the tip data from parent
  @Input() usersData: any[] = []; // Will receive users data from parent

  // The entry whose detail is open: one at a time, as on the other tables
  // that carry an expandable row
  // the ids of the rows opened, groups and entries alike
  expanded = new Set<string>();

  readonly typeOptions: TableFilterOption[] = [
    {id: 'Access', label: 'Access'},
    {id: 'Update', label: 'Update'},
    {id: 'Delete', label: 'Delete'}
  ];

  readonly table = new TableState<GroupedAuditLogEntry>({
    orderBy: 'timestamp',
    orderDesc: true,
    filters: {
      type: {type: 'select'}
    }
  });

  // Audit log data
  auditLogEntries: AuditLogEntry[] = [];

  ngOnInit() {
    this.loadAuditLogData();
  }

  getUserName(userId: string): string {
    // The whistleblower acts through the report it holds the session of, so
    // the report names it as much as an empty author does
    if (!userId || userId === this.tipId) {
      return this.translateService.instant('Whistleblower');
    }

    // Defensive check for users array
    if (!this.usersData || !Array.isArray(this.usersData)) {
      return userId; // Fallback to ID if no users data available
    }

    const user = this.usersData.find(u => u && u.id === userId);
    if (user) {
      return user.name;
    }

    // Return the ID if user not found (might be deleted user)
    return userId;
  }

  getUserDisplayName(userId: string): string {
    return this.getUserName(userId);
  }

  loadAuditLogData() {
    // Determine which API endpoint to use based on user role
    const userRole = this.authenticationService.session?.role;

    if (userRole === 'receiver' && this.tipId) {
      // Use recipient audit log API
      this.httpService.requestRecipientTipAuditLogResource(this.tipId).subscribe({
        next: (auditLogData: auditlogResolverModel[]) => {
          this.processAuditLogData(auditLogData);
        },
        error: (error) => {
          console.error('Error loading recipient audit log:', error);
          this.auditLogEntries = [];
        }
      });
    } else if (userRole === 'whistleblower') {
      // Use whistleblower audit log API
      this.httpService.requestWhistleblowerTipAuditLogResource().subscribe({
        next: (auditLogData: auditlogResolverModel[]) => {
          this.processAuditLogData(auditLogData);
        },
        error: (error) => {
          console.error('Error loading whistleblower audit log:', error);
          this.auditLogEntries = [];
        }
      });
    } else {
      // Fallback: no audit log data available
      this.auditLogEntries = [];
    }
  }

  private processAuditLogData(auditLogData: auditlogResolverModel[]) {
    this.auditLogEntries = auditLogData.map((log, index) => {
      return {
        id: `audit_${index}`,
        user: this.getUserName(log.user_id || ''),
        action: log.type,
        type: this.categorizeAuditLogType(log.type),
        timestamp: new Date(log.date),
        data: log.data,
        hash_sha256: log.data?.hash_sha256 || '',
        hash_sha512: log.data?.hash_sha512 || ''
      };
    });

    this.table.setItems(this.groupAccessReportEntries(this.auditLogEntries));

    // Zoneless: the entries arrive on an http callback, which notifies nothing on its own
    this.cdr.detectChanges();
  }

  private groupAccessReportEntries(entries: AuditLogEntry[]): GroupedAuditLogEntry[] {
    const grouped: GroupedAuditLogEntry[] = [];

    // Sort entries by timestamp (oldest first for sequential processing)
    const sortedEntries = [...entries].sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime());

    let i = 0;
    while (i < sortedEntries.length) {
      const currentEntry = sortedEntries[i];
      if (currentEntry === undefined) {
        break;
      }

      // Check if this is an access_report entry
      if (currentEntry.action === 'access_report') {
        const currentDayKey = currentEntry.timestamp.toISOString().split('T')[0];
        const groupEntries: AuditLogEntry[] = [currentEntry];

        // Look ahead to find consecutive access_report entries from the same user and same day
        let j = i + 1;
        while (j < sortedEntries.length) {
          const nextEntry = sortedEntries[j];
          if (nextEntry === undefined) {
            break;
          }
          const nextDayKey = nextEntry.timestamp.toISOString().split('T')[0];

          // Check if next entry is access_report, same user, and same day
          if (nextEntry.action === 'access_report' &&
              nextEntry.user === currentEntry.user &&
              nextDayKey === currentDayKey) {
            groupEntries.push(nextEntry);
            j++;
          } else {
            // Break the sequence if user alternates or different action/day
            break;
          }
        }

        // Create group or single entry based on count
        if (groupEntries.length === 1) {
          // Single entry - no need to group
          grouped.push({
            ...currentEntry,
            isGroup: false
          });
        } else {
          // Multiple consecutive entries - create a group
          const earliestEntry = currentEntry; // Already sorted oldest first

          grouped.push({
            ...earliestEntry,
            id: `group_${currentEntry.user}_${i}`,
            isGroup: true,
            groupedEntries: groupEntries.sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime()),
            groupCount: groupEntries.length
          });
        }

        // Move index to next unprocessed entry
        i = j;
      } else {
        // Non-access_report entries are added directly
        grouped.push({
          ...currentEntry,
          isGroup: false
        });
        i++;
      }
    }

    return grouped;
  }

  categorizeAuditLogType(auditLogType: string): string {
    // Categorize various audit log actions into broader types for filtering
    switch (auditLogType.toLowerCase()) {
      // Access actions
      case 'access_report':
      case 'whistleblower_access':
      case 'export_report':
      case 'scheduled_backup':
        return 'Access';

      // Update/modification actions
      case 'update_report_status':
      case 'update_report_expiration':
      case 'upload_file':
      case 'add_comment':
      case 'set_reminder':
      case 'grant_access':
      case 'mask_information':
      case 'auto_expiration_reminder':
        return 'Update';

      // Deletion actions
      case 'revoke_access':
      case 'delete_attachment':
      case 'delete_file':
      case 'delete_report':
        return 'Delete';

      // Default fallback
      default:
        // Try to infer from action name patterns
        if (auditLogType.includes('delete') || auditLogType.includes('remove') || auditLogType.includes('revoke')) {
          return 'Delete';
        } else if (auditLogType.includes('update') || auditLogType.includes('modify') || auditLogType.includes('change') ||
                   auditLogType.includes('add') || auditLogType.includes('grant') || auditLogType.includes('upload') ||
                   auditLogType.includes('mask') || auditLogType.includes('set')) {
          return 'Update';
        } else if (auditLogType.includes('access') || auditLogType.includes('view') || auditLogType.includes('download') ||
                   auditLogType.includes('export') || auditLogType.includes('backup')) {
          return 'Access';
        }
        return 'Access'; // Default to Access for unknown types
    }
  }

  // What a row can open: the entries it groups, or the details of the entry
  isExpandable(entry: GroupedAuditLogEntry): boolean {
    return !!entry.isGroup || this.hasDetails(entry);
  }

  // What an entry holds beyond its row: today the fingerprints of a deletion
  hasDetails(entry: AuditLogEntry): boolean {
    return !!entry.hash_sha256 || !!entry.hash_sha512;
  }

  isExpanded(entry: AuditLogEntry): boolean {
    return this.expanded.has(entry.id);
  }

  toggle(entry: AuditLogEntry) {
    if (this.expanded.has(entry.id)) {
      this.expanded.delete(entry.id);
    } else {
      this.expanded.add(entry.id);
    }
    this.cdr.detectChanges();
  }

  getTypeDotColor(actionType: string): string {
    switch (actionType.toLowerCase()) {
      case 'access':
        return 'text-info';  // Blue
      case 'delete':
        return 'text-danger'; // Red
      case 'update':
        return 'text-warning'; // Yellow
      default:
        return 'text-primary';
    }
  }

  exportTipAuditLog() {
    // Export what is on screen, filters included
    const filteredData = this.table.result;

    const exportData = filteredData.map(item => ({
      Date: new Date(item.timestamp).toLocaleString(),
      Type: item.type,
      Action: item.action,
      User: item.user,
      Fingerprint: item.hash_sha256 || '',
      Data: item.data ? JSON.stringify(item.data) : ''
    }));

    let filename = `tip_audit_log_${this.tipId}`;
    if (filteredData.length !== this.auditLogEntries.length) {
      filename += '_filtered';
    }

    this.utilsService.generateCSV(filename, exportData, ["Date", "Type", "Action", "User", "Fingerprint", "Data"]);
  }

  cancel() {
    this.activeModal.dismiss();
  }
}
