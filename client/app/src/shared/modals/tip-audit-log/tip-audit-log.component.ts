import {Component, Input, inject, OnInit, ChangeDetectorRef} from "@angular/core";
import {NgbActiveModal, NgbModal, NgbPagination, NgbPaginationPrevious, NgbPaginationNext, NgbPaginationFirst, NgbPaginationLast, NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {FormsModule} from "@angular/forms";
import {DatePipe, NgClass} from "@angular/common";
import {TranslateModule, TranslateService} from "@ngx-translate/core";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {IDropdownSettings, NgMultiSelectDropDownModule} from "ng-multiselect-dropdown";
import {HttpService} from "@app/shared/services/http.service";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {UtilsService} from "@app/shared/services/utils.service";
import {auditlogResolverModel} from "@app/models/resolvers/auditlog-resolver-model";
import {AppDataService} from "@app/app-data.service";
import {TipAuditLogService} from "@app/shared/services/tip-audit-log.service";

interface AuditLogEntry {
  id: string;
  user: string;
  action: string;
  type: string;
  timestamp: Date;
  data?: any;
  detail?: string;
  isNew?: boolean;
}

interface GroupedAuditLogEntry {
  id: string;
  user: string;
  action: string;
  type: string;
  timestamp: Date;
  data?: any;
  detail?: string;
  isGroup?: boolean;
  isExpanded?: boolean;
  groupedEntries?: AuditLogEntry[];
  groupCount?: number;
  isNew?: boolean;
  hasNewEntries?: boolean;
}

@Component({
  selector: "src-tip-audit-log",
  templateUrl: "./tip-audit-log.component.html",
  standalone: true,
  imports: [FormsModule, DatePipe, NgClass, TranslateModule, TranslatorPipe, NgMultiSelectDropDownModule, NgbPagination, NgbPaginationPrevious, NgbPaginationNext, NgbPaginationFirst, NgbPaginationLast, NgbTooltipModule],
  providers: [DatePipe],
  styles: [`
    .table {
      table-layout: fixed;
    }
    .table tbody tr.new-entry-highlight {
      background-color: #fffbf0 !important;
    }
    .table tbody tr.new-entry-highlight:hover {
      background-color: #fff9e6 !important;
    }
    .table tbody tr.new-entry-highlight > td {
      background-color: inherit !important;
    }
  `]
})

export class TipAuditLogComponent implements OnInit {
  private modalService = inject(NgbModal);
  private activeModal = inject(NgbActiveModal);
  private translateService = inject(TranslateService);
  private httpService = inject(HttpService);
  private authenticationService = inject(AuthenticationService);
  private utilsService = inject(UtilsService);
  private appDataService = inject(AppDataService);
  private cdr = inject(ChangeDetectorRef);
  private datePipe = inject(DatePipe);
  private tipAuditLogService = inject(TipAuditLogService);

  @Input() tipId: string = '';
  @Input() tipData: any = null; // Will receive the tip data from parent
  @Input() usersData: any[] = [];
  @Input() lastAccess?: string; // Last time user accessed the tip (from backend)

  // Component state
  searchTerm: string = '';
  sortField: string = 'timestamp';
  sortDirection: 'asc' | 'desc' = 'desc';

  // Pagination properties
  currentPage = 1;
  pageSize = 10;

  // Type filtering properties
  dropdownTypeModel: { id: number; label: string; color?: string; }[] = [];
  dropdownTypeData: { id: number; label: string; color?: string; }[] = [];
  typeDropdownVisible: boolean = false;

  // Dropdown settings
  dropdownSettings: IDropdownSettings = {
    idField: "id",
    textField: "label",
    itemsShowLimit: 3,
    allowSearchFilter: false,
    selectAllText: this.translateService.instant("Select all"),
    unSelectAllText: this.translateService.instant("Deselect all"),
    searchPlaceholderText: this.translateService.instant("Search")
  };

  // Audit log data
  auditLogEntries: AuditLogEntry[] = [];
  displayedEntries: GroupedAuditLogEntry[] = [];
  lastAuditLogAccess: Date | null = null;
  newEntriesCount: number = 0;

  ngOnInit() {
    this.initializeTypeFilterData();

    // Use the more recent of: last audit log view or last tip access
    const lastAuditLogView = this.tipAuditLogService.getLastAuditLogView(this.tipId);

    if (lastAuditLogView) {
      this.lastAuditLogAccess = lastAuditLogView;
    } else if (this.lastAccess) {
      // Fallback to tip's last_access if audit log was never viewed
      this.lastAuditLogAccess = new Date(this.lastAccess);
    }

    this.loadAuditLogData();
  }

  getUserName(userId: string): string {
    if (!userId) {
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

  initializeTypeFilterData() {
    this.dropdownTypeData = [
      { id: 1, label: 'Access', color: 'info' },
      { id: 2, label: 'Update', color: 'warning' },
      { id: 3, label: 'Delete', color: 'danger' }
    ];
  }

  loadAuditLogData() {
    // Determine which API endpoint to use based on user role
    const userRole = this.authenticationService.session.role;

    if (userRole === 'receiver' && this.tipId) {
      // Use recipient audit log API
      this.httpService.requestRecipientTipAuditLogResource(this.tipId).subscribe({
        next: (auditLogData: auditlogResolverModel[]) => {
          this.processAuditLogData(auditLogData);
        },
        error: (error) => {
          console.error('Error loading recipient audit log:', error);
          this.auditLogEntries = [];
          // Mark as viewed even on error
          if (this.tipId) {
            this.tipAuditLogService.markAuditLogAsViewed(this.tipId);
          }
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
          // Mark as viewed even on error
          if (this.tipId) {
            this.tipAuditLogService.markAuditLogAsViewed(this.tipId);
          }
        }
      });
    } else if (userRole === 'admin' && this.tipId) {
      // Use admin audit log API
      this.httpService.requestAdminAuditLogByObjectResource(this.tipId).subscribe({
        next: (auditLogData: auditlogResolverModel[]) => {
          this.processAuditLogData(auditLogData);
        },
        error: (error) => {
          console.error('Error loading admin audit log:', error);
          this.auditLogEntries = [];
          // Mark as viewed even on error
          if (this.tipId) {
            this.tipAuditLogService.markAuditLogAsViewed(this.tipId);
          }
        }
      });
    } else {
      // Fallback: no audit log data available
      this.auditLogEntries = [];
      this.createDisplayedEntries();

      // Mark as viewed even if no data
      if (this.tipId) {
        this.tipAuditLogService.markAuditLogAsViewed(this.tipId);
      }
    }
  }

  private processAuditLogData(auditLogData: auditlogResolverModel[]) {
    this.auditLogEntries = auditLogData.map((log, index) => {
      const actionInfo = this.formatActionText(log);
      const entryTimestamp = new Date(log.date);
      const isNew = this.lastAuditLogAccess ? entryTimestamp > this.lastAuditLogAccess : false;

      if (isNew) {
        this.newEntriesCount++;
      }

      return {
        id: `audit_${index}`,
        user: this.getUserName(log.user_id || ''),
        action: actionInfo.action,
        detail: actionInfo.detail,
        type: this.categorizeAuditLogType(log.type),
        timestamp: entryTimestamp,
        data: log.data,
        isNew: isNew
      };
    });

    this.createDisplayedEntries();

    // Mark audit log as viewed after data is processed
    if (this.tipId) {
      this.tipAuditLogService.markAuditLogAsViewed(this.tipId);
    }
  }

  private formatActionText(log: auditlogResolverModel): { action: string, detail?: string } {
    const userRole = this.authenticationService.session.role;
    const isAdminOrAuditor = userRole === 'admin' || userRole === 'auditor';

    // Check common actions shown to all roles
    const commonResult = this.formatCommonActions(log);
    if (commonResult) return commonResult;

    // For admin/auditor, only show details for status and expiration changes
    if (isAdminOrAuditor) return { action: log.type };

    // Format details for recipients and whistleblowers
    return this.formatRecipientWhistleblowerActions(log);
  }

  private formatCommonActions(log: auditlogResolverModel): { action: string, detail?: string } | null {
    if (log.type === 'update_report_status' && log.data?.status) {
      const statusLabel = this.utilsService.getSubmissionStatusText(
        log.data.status, log.data.substatus || '', this.appDataService.submissionStatuses
      );
      if (statusLabel) return { action: log.type, detail: statusLabel };
    }

    if (log.type === 'update_report_expiration' && log.data?.curr_expiration_date) {
      const expirationDate = this.datePipe.transform(log.data.curr_expiration_date * 1000, 'dd-MM-yyyy');
      if (expirationDate) return { action: log.type, detail: expirationDate };
    }

    return null;
  }

  private formatRecipientWhistleblowerActions(log: auditlogResolverModel): { action: string, detail?: string } {
    const handlers: Record<string, () => { action: string, detail?: string }> = {
      'grant_access': () => this.formatAccessAction(log),
      'revoke_access': () => this.formatAccessAction(log),
      'transfer_access': () => this.formatAccessAction(log),
      'update_redaction': () => this.formatRedactionAction(log),
      'set_reminder': () => this.formatReminderAction(log),
      'upload_file': () => this.formatFileUploadAction(log),
      'delete_attachment': () => this.formatFileDeletionAction(log),
      'whistleblower_login': () => ({ action: log.type, detail: this.translateService.instant('Whistleblower') }),
      'whistleblower_access': () => ({ action: log.type, detail: this.translateService.instant('Whistleblower') }),
      'export_report': () => this.formatExportAction(log)
    };

    return handlers[log.type]?.() || { action: log.type };
  }

  private formatAccessAction(log: auditlogResolverModel): { action: string, detail?: string } {
    if (log.data?.recipient_id) {
      return { action: log.type, detail: this.getUserName(log.data.recipient_id) };
    }
    return { action: log.type };
  }

  private formatRedactionAction(log: auditlogResolverModel): { action: string, detail?: string } {
    if (!log.data) return { action: log.type };

    const details: string[] = [];
    this.addTemporaryRedactionDetail(log.data, details);
    this.addPermanentRedactionDetail(log.data, details);

    return details.length > 0 ? { action: log.type, detail: details.join(', ') } : { action: log.type };
  }

  private addTemporaryRedactionDetail(data: any, details: string[]): void {
    if (data.new_temporary_redaction === undefined) return;
    if (data.old_temporary_redaction === data.new_temporary_redaction) return;

    const status = data.new_temporary_redaction ?
      this.translateService.instant('Masked') : this.translateService.instant('Unmasked');
    details.push(this.translateService.instant('Temporary') + ': ' + status);
  }

  private addPermanentRedactionDetail(data: any, details: string[]): void {
    if (data.permanent_redaction === undefined) return;
    if (data.old_permanent_redaction === data.permanent_redaction) return;

    const status = data.permanent_redaction ?
      this.translateService.instant('Redacted') : this.translateService.instant('Unredacted');
    details.push(this.translateService.instant('Permanent') + ': ' + status);
  }

  private formatReminderAction(log: auditlogResolverModel): { action: string, detail?: string } {
    if (log.data?.reminder_date) {
      const reminderDate = this.datePipe.transform(log.data.reminder_date * 1000, 'dd-MM-yyyy');
      if (reminderDate) return { action: log.type, detail: reminderDate };
    }
    return { action: log.type };
  }

  private formatFileUploadAction(log: auditlogResolverModel): { action: string, detail?: string } {
    if (log.data?.filename) return { action: log.type, detail: log.data.filename };
    if (log.data?.file_type) return { action: log.type, detail: log.data.file_type };
    return { action: log.type };
  }

  private formatFileDeletionAction(log: auditlogResolverModel): { action: string, detail?: string } {
    if (!log.data?.file_type) return { action: log.type };

    const extension = this.extractFileExtension(log.data.file_type);
    if (extension && this.isValidExtension(extension)) {
      return { action: log.type, detail: extension };
    }
    return { action: log.type };
  }

  private extractFileExtension(fileType: string): string | null {
    const mimeParts = fileType.split('/');
    if (mimeParts.length !== 2) return null;

    let extension = mimeParts[1];
    if (extension.includes('.')) {
      extension = extension.split('.').pop() || extension;
    }
    return extension;
  }

  private isValidExtension(extension: string): boolean {
    return extension.length < 20 && !extension.includes('=');
  }

  private formatExportAction(log: auditlogResolverModel): { action: string, detail?: string } {
    if (log.data?.format) return { action: log.type, detail: log.data.format.toUpperCase() };
    return { action: log.type };
  }

  private createDisplayedEntries() {
    // Apply initial filters to raw data before grouping
    let preFiltered = this.auditLogEntries;

    // Apply search filter to raw data
    if (this.searchTerm.trim()) {
      const searchLower = this.searchTerm.toLowerCase();
      preFiltered = preFiltered.filter(entry =>
        entry.user.toLowerCase().includes(searchLower) ||
        entry.action.toLowerCase().includes(searchLower) ||
        entry.type.toLowerCase().includes(searchLower)
      );
    }

    // Apply type filter to raw data
    if (this.dropdownTypeModel && this.dropdownTypeModel.length > 0) {
      const selectedCategories = this.dropdownTypeModel.map(item => item.label);
      preFiltered = preFiltered.filter(entry => selectedCategories.includes(entry.type));
    }

    this.displayedEntries = this.groupAccessReportEntries(preFiltered);
  }

  private groupAccessReportEntries(entries: AuditLogEntry[]): GroupedAuditLogEntry[] {
    const grouped: GroupedAuditLogEntry[] = [];
    const sortedEntries = [...entries].sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime());

    let i = 0;
    while (i < sortedEntries.length) {
      const currentEntry = sortedEntries[i];

      if (currentEntry.action === 'access_report') {
        const { groupEntries, nextIndex } = this.collectConsecutiveAccessReports(sortedEntries, i);
        this.addGroupedOrSingleEntry(grouped, groupEntries, currentEntry, i);
        i = nextIndex;
      } else {
        grouped.push({ ...currentEntry, isGroup: false });
        i++;
      }
    }

    return grouped.sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime());
  }

  private collectConsecutiveAccessReports(sortedEntries: AuditLogEntry[], startIndex: number) {
    const currentEntry = sortedEntries[startIndex];
    const currentDayKey = this.getDayKey(currentEntry.timestamp);
    const groupEntries: AuditLogEntry[] = [currentEntry];

    let j = startIndex + 1;
    while (j < sortedEntries.length && this.shouldGroupWithCurrent(sortedEntries[j], currentEntry, currentDayKey)) {
      groupEntries.push(sortedEntries[j]);
      j++;
    }

    return { groupEntries, nextIndex: j };
  }

  private shouldGroupWithCurrent(nextEntry: AuditLogEntry, currentEntry: AuditLogEntry, currentDayKey: string): boolean {
    const nextDayKey = this.getDayKey(nextEntry.timestamp);
    return nextEntry.action === 'access_report' &&
           nextEntry.user === currentEntry.user &&
           nextDayKey === currentDayKey;
  }

  private getDayKey(timestamp: Date): string {
    return timestamp.toISOString().split('T')[0];
  }

  private addGroupedOrSingleEntry(grouped: GroupedAuditLogEntry[], groupEntries: AuditLogEntry[], currentEntry: AuditLogEntry, index: number): void {
    if (groupEntries.length === 1) {
      grouped.push({ ...groupEntries[0], isGroup: false });
    } else {
      const earliestEntry = groupEntries[0];
      const hasNewEntries = groupEntries.some(entry => entry.isNew);

      grouped.push({
        ...earliestEntry,
        id: `group_${currentEntry.user}_${index}`,
        isGroup: true,
        isExpanded: false,
        groupedEntries: groupEntries.sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime()),
        groupCount: groupEntries.length,
        hasNewEntries: hasNewEntries
      });
    }
  }

  categorizeAuditLogType(auditLogType: string): string {
    // Categorize various audit log actions into broader types for filtering
    switch (auditLogType.toLowerCase()) {
      // Access actions
      case 'access_report':
      case 'whistleblower_access':
      case 'whistleblower_login':
      case 'export_report':
      case 'scheduled_backup':
        return 'Access';

      // Update/modification actions
      case 'update_report_status':
      case 'update_report_expiration':
      case 'update_redaction':
      case 'upload_file':
      case 'add_comment':
      case 'set_reminder':
      case 'grant_access':
      case 'transfer_access':
      case 'mask_information':
      case 'auto_expiration_reminder':
        return 'Update';

      // Deletion actions
      case 'revoke_access':
      case 'delete_attachment':
      case 'delete_report':
        return 'Delete';

      // Default fallback
      default:
        // Try to infer from action name patterns
        if (auditLogType.includes('delete') || auditLogType.includes('remove') || auditLogType.includes('revoke')) {
          return 'Delete';
        } else if (auditLogType.includes('update') || auditLogType.includes('modify') || auditLogType.includes('change') ||
                   auditLogType.includes('add') || auditLogType.includes('grant') || auditLogType.includes('upload') ||
                   auditLogType.includes('mask') || auditLogType.includes('set') || auditLogType.includes('transfer')) {
          return 'Update';
        } else if (auditLogType.includes('access') || auditLogType.includes('view') || auditLogType.includes('download') ||
                   auditLogType.includes('export') || auditLogType.includes('backup') || auditLogType.includes('login')) {
          return 'Access';
        }
        return 'Access'; // Default to Access for unknown types
    }
  }

  toggleGroupExpansion(entry: GroupedAuditLogEntry) {
    if (entry.isGroup) {
      entry.isExpanded = !entry.isExpanded;
      this.cdr.detectChanges();
    }
  }

  onSearchChange() {
    this.currentPage = 1; // Reset to first page when searching
    this.createDisplayedEntries();
  }

  toggleSort(field: string) {
    if (this.sortField === field) {
      this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
    } else {
      this.sortField = field;
      this.sortDirection = 'asc';
    }
    this.currentPage = 1; // Reset to first page when sorting
    this.createDisplayedEntries();
  }

  onTypeFilterChange(model: { id: number; label: string; }[]) {
    this.dropdownTypeModel = model;
    this.currentPage = 1; // Reset to first page when filtering
    this.createDisplayedEntries();
  }

  toggleTypeDropdown() {
    this.typeDropdownVisible = !this.typeDropdownVisible;
  }

  checkTypeFilter(model: { id: number; label: string; }[]): boolean {
    return model && model.length > 0;
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

  getFilteredData(): GroupedAuditLogEntry[] {
    return this.getFilteredAndExpandedData();
  }

  private getFilteredAndExpandedData(): GroupedAuditLogEntry[] {
    // Get the pre-filtered and grouped data
    let sortedEntries = [...this.displayedEntries];

    // Apply sorting
    sortedEntries = sortedEntries.sort((a, b) => {
      let aValue: any, bValue: any;

      switch (this.sortField) {
        case 'user':
          aValue = a.user.toLowerCase();
          bValue = b.user.toLowerCase();
          break;
        case 'action':
          aValue = a.action.toLowerCase();
          bValue = b.action.toLowerCase();
          break;
        case 'type':
          aValue = a.type.toLowerCase();
          bValue = b.type.toLowerCase();
          break;
        case 'timestamp':
          aValue = a.timestamp.getTime();
          bValue = b.timestamp.getTime();
          break;
        default:
          aValue = a.timestamp.getTime();
          bValue = b.timestamp.getTime();
      }

      if (aValue < bValue) {
        return this.sortDirection === 'asc' ? -1 : 1;
      }
      if (aValue > bValue) {
        return this.sortDirection === 'asc' ? 1 : -1;
      }
      return 0;
    });

    return sortedEntries;
  }

  getPaginatedData(): GroupedAuditLogEntry[] {
    const filteredData = this.getFilteredData();
    const startIndex = (this.currentPage - 1) * this.pageSize;
    const endIndex = startIndex + this.pageSize;
    return filteredData.slice(startIndex, endIndex);
  }

  exportTipAuditLog() {
    // Get the filtered data for export
    const filteredData = this.getFilteredData();

    // Prepare filter metadata
    const filterInfo = this.getFilterMetadata();

    // Transform data to include all necessary information for export
    const exportData = filteredData.map(item => ({
      Date: new Date(item.timestamp).toLocaleString(),
      Type: item.type,
      Action: item.action,
      User: item.user,
      'Raw Data': item.data ? JSON.stringify(item.data) : ''
    }));

    // Create filename with filter information
    const timestamp = new Date().toISOString().slice(0, 19).replace(/[:-]/g, '');
    let filename = `tip_audit_log_${this.tipId}_${timestamp}`;

    if (filterInfo.hasFilters) {
      filename += '_filtered';
    }

    // Add filter metadata as a comment in the CSV if filters are applied
    let csvData = exportData;
    if (filterInfo.hasFilters) {
      // Add filter information as the first rows
      const filterRows = [
        { Date: '# FILTER INFORMATION', Type: '', Action: '', User: '', 'Raw Data': '' },
        { Date: `# Search Term: ${filterInfo.searchTerm || 'None'}`, Type: '', Action: '', User: '', 'Raw Data': '' },
        { Date: `# Type Filters: ${filterInfo.typeFilters}`, Type: '', Action: '', User: '', 'Raw Data': '' },
        { Date: `# Export Date: ${new Date().toLocaleString()}`, Type: '', Action: '', User: '', 'Raw Data': '' },
        { Date: `# Total Entries: ${filteredData.length}`, Type: '', Action: '', User: '', 'Raw Data': '' },
        { Date: '', Type: '', Action: '', User: '', 'Raw Data': '' }, // Empty row for separation
      ];
      csvData = [...filterRows, ...exportData];
    }

    this.utilsService.generateCSV(filename, csvData, ["Date", "Type", "Action", "User", "Raw Data"]);
  }

  private getFilterMetadata() {
    const hasSearchFilter = this.searchTerm.trim().length > 0;
    const hasTypeFilter = this.dropdownTypeModel && this.dropdownTypeModel.length > 0;

    let typeFilters = 'All';
    if (hasTypeFilter) {
      typeFilters = this.dropdownTypeModel.map(item => item.label).join(', ');
    }

    return {
      hasFilters: hasSearchFilter || hasTypeFilter,
      searchTerm: this.searchTerm.trim(),
      typeFilters: typeFilters,
      totalEntries: this.auditLogEntries.length,
      filteredEntries: this.getFilteredData().length
    };
  }

  cancel() {
    this.activeModal.dismiss();
  }
}
