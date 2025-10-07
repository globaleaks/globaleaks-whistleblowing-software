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

interface AuditLogEntry {
  id: string;
  user: string;
  action: string;
  type: string;
  timestamp: Date;
  data?: any;
}

interface GroupedAuditLogEntry {
  id: string;
  user: string;
  action: string;
  type: string;
  timestamp: Date;
  data?: any;
  isGroup?: boolean;
  isExpanded?: boolean;
  groupedEntries?: AuditLogEntry[];
  groupCount?: number;
}

@Component({
  selector: "src-tip-audit-log",
  templateUrl: "./tip-audit-log.component.html",
  standalone: true,
  imports: [FormsModule, DatePipe, NgClass, TranslateModule, TranslatorPipe, NgMultiSelectDropDownModule, NgbPagination, NgbPaginationPrevious, NgbPaginationNext, NgbPaginationFirst, NgbPaginationLast, NgbTooltipModule],
  styles: [`
    .table {
      table-layout: fixed;
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
  private cdr = inject(ChangeDetectorRef);

  @Input() tipId: string = '';
  @Input() tipData: any = null; // Will receive the tip data from parent
  @Input() usersData: any[] = []; // Will receive users data from parent

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

  ngOnInit() {
    this.initializeTypeFilterData();
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
        data: log.data
      };
    });

    this.createDisplayedEntries();
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
    
    // Sort entries by timestamp (oldest first for sequential processing)
    const sortedEntries = [...entries].sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime());
    
    let i = 0;
    while (i < sortedEntries.length) {
      const currentEntry = sortedEntries[i];
      
      // Check if this is an access_report entry
      if (currentEntry.action === 'access_report') {
        const currentDayKey = currentEntry.timestamp.toISOString().split('T')[0];
        const groupEntries: AuditLogEntry[] = [currentEntry];
        
        // Look ahead to find consecutive access_report entries from the same user and same day
        let j = i + 1;
        while (j < sortedEntries.length) {
          const nextEntry = sortedEntries[j];
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
            ...groupEntries[0],
            isGroup: false
          });
        } else {
          // Multiple consecutive entries - create a group
          const earliestEntry = groupEntries[0]; // Already sorted oldest first
          
          grouped.push({
            ...earliestEntry,
            id: `group_${currentEntry.user}_${i}`,
            isGroup: true,
            isExpanded: false,
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
    
    // Sort the final array by timestamp (newest first for display)
    return grouped.sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime());
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
