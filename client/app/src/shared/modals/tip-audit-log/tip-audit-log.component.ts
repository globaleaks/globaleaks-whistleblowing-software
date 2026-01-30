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
  tipId: string;
  user: string;
  action: string;
  type: string;
  timestamp: Date;
  data?: any;
}

interface GroupedAuditLogEntry {
  id: string;
  tipId: string;
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
  @Input() tipData: any = null;
  @Input() usersData: any[] = [];
  @Input() userData: any;
  @Input() name: string = '';
  @Input() auditLogsByTip: any = null;

  searchTerm: string = '';
  sortField: string = 'timestamp';
  sortDirection: 'asc' | 'desc' = 'desc';
  showTipColumn: boolean = false;

  currentPage = 1;
  pageSize = 10;

  dropdownTypeModel: { id: number; label: string; color?: string; }[] = [];
  dropdownTypeData: { id: number; label: string; color?: string; }[] = [];
  typeDropdownVisible: boolean = false;

  dropdownTipModel: { id: string; label: string; }[] = [];
  dropdownTipData: { id: string; label: string; }[] = [];
  tipDropdownVisible: boolean = false;

  dropdownSettings: IDropdownSettings = {
    idField: "id",
    textField: "label",
    itemsShowLimit: 3,
    allowSearchFilter: false,
    selectAllText: this.translateService.instant("Select all"),
    unSelectAllText: this.translateService.instant("Deselect all"),
    searchPlaceholderText: this.translateService.instant("Search")
  };

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

    if (!this.usersData || !Array.isArray(this.usersData)) {
      return userId;
    }

    const user = this.usersData.find(u => u && u.id === userId);
    if (user) {
      return user.name;
    }
    if (this.name === 'tips_list' && this.userData && this.userData.id === userId) {
      return this.userData.name;
    }
    return userId;
  }

  initializeTypeFilterData() {
    this.dropdownTypeData = [
      { id: 1, label: 'Access', color: 'info' },
      { id: 2, label: 'Update', color: 'warning' },
      { id: 3, label: 'Delete', color: 'danger' }
    ];
  }

  initializeTipFilterData() {
    const uniqueTipIds = [...new Set(this.auditLogEntries.map(entry => entry.tipId))];
    
    this.dropdownTipData = uniqueTipIds.map(tipId => ({
      id: tipId,
      label: tipId
    })).sort((a, b) => a.label.localeCompare(b.label));
  }

  loadAuditLogData() {
    if (this.name === 'tips_list' && this.auditLogsByTip) {
      this.processBulkAuditLogs(this.auditLogsByTip);
      this.showTipColumn = true;
    } else {
      const userRole = this.authenticationService.session.role;
      
      if (userRole === 'receiver' && this.tipId) {
        this.httpService.requestRecipientTipAuditLogResource(this.tipId).subscribe({
          next: (auditLogData: auditlogResolverModel[]) => {
            this.processSingleTipAuditLogs(auditLogData, this.tipId);
          },
          error: () => this.auditLogEntries = []
        });
      } else if (userRole === 'whistleblower') {
        this.httpService.requestWhistleblowerTipAuditLogResource().subscribe({
          next: (auditLogData: auditlogResolverModel[]) => {
            this.processSingleTipAuditLogs(auditLogData, this.tipId);
          },
          error: () => this.auditLogEntries = []
        });
      } else {
        this.auditLogEntries = [];
      }
      this.showTipColumn = false;
    }
  }

  private processBulkAuditLogs(auditLogsByTip: any) {
    this.auditLogEntries = [];
    let index = 0;

    Object.keys(auditLogsByTip).forEach(tipId => {
      const tipLogs = auditLogsByTip[tipId];
      
      tipLogs.forEach((log: any) => {
        this.auditLogEntries.push({
          id: `audit_${index}`,
          tipId: tipId,
          user: this.getUserName(log.user_id || ''),
          action: log.type,
          type: this.categorizeAuditLogType(log.type),
          timestamp: new Date(log.date),
          data: log.data
        });
        index++;
      });
    });

    this.initializeTipFilterData();
    this.createDisplayedEntries();
  }

  private processSingleTipAuditLogs(auditLogData: auditlogResolverModel[], tipId: string) {
    this.auditLogEntries = auditLogData.map((log, index) => {
      return {
        id: `audit_${index}`,
        tipId: tipId,
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
    let preFiltered = this.auditLogEntries;

    if (this.searchTerm.trim()) {
      const searchLower = this.searchTerm.toLowerCase();
      preFiltered = preFiltered.filter(entry =>
        entry.user.toLowerCase().includes(searchLower) ||
        entry.action.toLowerCase().includes(searchLower) ||
        entry.type.toLowerCase().includes(searchLower) ||
        entry.tipId.toLowerCase().includes(searchLower)
      );
    }

    if (this.dropdownTypeModel && this.dropdownTypeModel.length > 0) {
      const selectedCategories = this.dropdownTypeModel.map(item => item.label);
      preFiltered = preFiltered.filter(entry => selectedCategories.includes(entry.type));
    }

    if (this.showTipColumn && this.dropdownTipModel && this.dropdownTipModel.length > 0) {
      const selectedTipIds = this.dropdownTipModel.map(item => item.id);
      preFiltered = preFiltered.filter(entry => selectedTipIds.includes(entry.tipId));
    }

    this.displayedEntries = this.groupAccessReportEntries(preFiltered);
  }

  private groupAccessReportEntries(entries: AuditLogEntry[]): GroupedAuditLogEntry[] {
    const grouped: GroupedAuditLogEntry[] = [];

    const entriesByTip = new Map<string, AuditLogEntry[]>();
    
    entries.forEach(entry => {
      if (!entriesByTip.has(entry.tipId)) {
        entriesByTip.set(entry.tipId, []);
      }
      entriesByTip.get(entry.tipId)!.push(entry);
    });

    entriesByTip.forEach((tipEntries, tipId) => {
      const sortedEntries = [...tipEntries].sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime());

      let i = 0;
      while (i < sortedEntries.length) {
        const currentEntry = sortedEntries[i];

        if (currentEntry.action === 'access_report') {
          const currentDayKey = currentEntry.timestamp.toISOString().split('T')[0];
          const groupEntries: AuditLogEntry[] = [currentEntry];

          let j = i + 1;
          while (j < sortedEntries.length) {
            const nextEntry = sortedEntries[j];
            const nextDayKey = nextEntry.timestamp.toISOString().split('T')[0];

            if (nextEntry.action === 'access_report' &&
                nextEntry.user === currentEntry.user &&
                nextDayKey === currentDayKey &&
                nextEntry.tipId === currentEntry.tipId) {
              groupEntries.push(nextEntry);
              j++;
            } else {
              break;
            }
          }

          if (groupEntries.length === 1) {
            grouped.push({
              ...groupEntries[0],
              isGroup: false
            });
          } else {
            const earliestEntry = groupEntries[0];
            
            grouped.push({
              ...earliestEntry,
              id: `group_${tipId}_${currentEntry.user}_${i}`,
              isGroup: true,
              isExpanded: false,
              groupedEntries: groupEntries.sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime()),
              groupCount: groupEntries.length
            });
          }

          i = j;
        } else {
          grouped.push({
            ...currentEntry,
            isGroup: false
          });
          i++;
        }
      }
    });

    return grouped.sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime());
  }

  categorizeAuditLogType(auditLogType: string): string {
    switch (auditLogType.toLowerCase()) {
      case 'access_report':
      case 'whistleblower_access':
      case 'export_report':
      case 'scheduled_backup':
        return 'Access';

      case 'update_report_status':
      case 'update_report_expiration':
      case 'upload_file':
      case 'add_comment':
      case 'set_reminder':
      case 'grant_access':
      case 'mask_information':
      case 'auto_expiration_reminder':
      case 'whistleblower_new_report':
        return 'Update';

      case 'revoke_access':
      case 'delete_attachment':
      case 'delete_report':
        return 'Delete';

      default:
        if (auditLogType.includes('delete') || auditLogType.includes('remove') || auditLogType.includes('revoke')) {
          return 'Delete';
        } else if (auditLogType.includes('update') || auditLogType.includes('modify') || auditLogType.includes('change') ||
                   auditLogType.includes('add') || auditLogType.includes('grant') || auditLogType.includes('upload') ||
                   auditLogType.includes('mask') || auditLogType.includes('set') || auditLogType.includes('new')) {
          return 'Update';
        } else if (auditLogType.includes('access') || auditLogType.includes('view') || auditLogType.includes('download') ||
                   auditLogType.includes('export') || auditLogType.includes('backup')) {
          return 'Access';
        }
        return 'Access';
    }
  }

  toggleGroupExpansion(entry: GroupedAuditLogEntry) {
    if (entry.isGroup) {
      entry.isExpanded = !entry.isExpanded;
      this.cdr.detectChanges();
    }
  }

  onSearchChange() {
    this.currentPage = 1;
    this.createDisplayedEntries();
  }

  toggleSort(field: string) {
    if (this.sortField === field) {
      this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
    } else {
      this.sortField = field;
      this.sortDirection = 'asc';
    }
    this.currentPage = 1;
    this.createDisplayedEntries();
  }

  onTypeFilterChange(model: { id: number; label: string; }[]) {
    this.dropdownTypeModel = model;
    this.currentPage = 1;
    this.createDisplayedEntries();
  }

  onTipFilterChange(model: { id: string; label: string; }[]) {
    this.dropdownTipModel = model;
    this.currentPage = 1;
    this.createDisplayedEntries();
  }

  toggleTypeDropdown() {
    this.typeDropdownVisible = !this.typeDropdownVisible;
    if (this.typeDropdownVisible && this.tipDropdownVisible) {
      this.tipDropdownVisible = false;
    }
  }

  toggleTipDropdown() {
    this.tipDropdownVisible = !this.tipDropdownVisible;
    if (this.tipDropdownVisible && this.typeDropdownVisible) {
      this.typeDropdownVisible = false;
    }
  }

  checkTypeFilter(model: { id: number; label: string; }[]): boolean {
    return model && model.length > 0;
  }

  checkTipFilter(model: { id: string; label: string; }[]): boolean {
    return model && model.length > 0;
  }

  getTypeDotColor(actionType: string): string {
    switch (actionType.toLowerCase()) {
      case 'access':
        return 'text-info';
      case 'delete':
        return 'text-danger';
      case 'update':
        return 'text-warning';
      default:
        return 'text-primary';
    }
  }

  getFilteredData(): GroupedAuditLogEntry[] {
    return this.getFilteredAndExpandedData();
  }

  private getFilteredAndExpandedData(): GroupedAuditLogEntry[] {
    let sortedEntries = [...this.displayedEntries];

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
      const filteredData = this.getFilteredData();
      const filterInfo = this.getFilterMetadata();
  
      const exportData = filteredData.map(item => {
        if (item.isGroup && item.groupedEntries) {
          return item.groupedEntries.map(childEntry => ({
            Date: new Date(childEntry.timestamp).toLocaleString(),
            Tip: childEntry.tipId,
            Type: childEntry.type,
            Action: childEntry.action,
            User: childEntry.user,
            'Raw Data': childEntry.data ? JSON.stringify(childEntry.data) : ''
          }));
        } else {
          return [{
            Date: new Date(item.timestamp).toLocaleString(),
            Tip: item.tipId,
            Type: item.type,
            Action: item.action,
            User: item.user,
            'Raw Data': item.data ? JSON.stringify(item.data) : ''
          }];
        }
      }).flat();
  
      const timestamp = new Date().toISOString().slice(0, 19).replace(/[:-]/g, '');
      let filename = this.tipId 
        ? `tip_audit_log_${this.tipId}_${timestamp}`
        : `all_tips_audit_log_${timestamp}`;
  
      if (filterInfo.hasFilters) {
        filename += '_filtered';
      }
  
      let csvData = exportData;
      if (filterInfo.hasFilters) {
        const filterRows = [
          { Date: '# FILTER INFORMATION', Tip: '', Type: '', Action: '', User: '', 'Raw Data': '' },
          { Date: `# Search Term: ${filterInfo.searchTerm || 'None'}`, Tip: '', Type: '', Action: '', User: '', 'Raw Data': '' },
          { Date: `# Type Filters: ${filterInfo.typeFilters}`, Tip: '', Type: '', Action: '', User: '', 'Raw Data': '' },
          { Date: `# Tip Filters: ${filterInfo.tipFilters}`, Tip: '', Type: '', Action: '', User: '', 'Raw Data': '' },
          { Date: `# Export Date: ${new Date().toLocaleString()}`, Tip: '', Type: '', Action: '', User: '', 'Raw Data': '' },
          { Date: `# Total Entries: ${filterInfo.totalEntries}`, Tip: '', Type: '', Action: '', User: '', 'Raw Data': '' },
          { Date: `# Filtered Entries: ${filterInfo.filteredEntries}`, Tip: '', Type: '', Action: '', User: '', 'Raw Data': '' },
          { Date: '', Tip: '', Type: '', Action: '', User: '', 'Raw Data': '' },
        ];
        csvData = [...filterRows, ...exportData];
      }
  
      const headers = this.showTipColumn 
        ? ["Date", "Tip", "Type", "Action", "User", "Raw Data"]
        : ["Date", "Type", "Action", "User", "Raw Data"];
  
      this.utilsService.generateCSV(filename, csvData, headers);
  }

  private getFilterMetadata() {
    const hasSearchFilter = this.searchTerm.trim().length > 0;
    const hasTypeFilter = this.dropdownTypeModel && this.dropdownTypeModel.length > 0;
    const hasTipFilter = this.showTipColumn && this.dropdownTipModel && this.dropdownTipModel.length > 0;

    let typeFilters = 'All';
    if (hasTypeFilter) {
      typeFilters = this.dropdownTypeModel.map(item => item.label).join(', ');
    }

    let tipFilters = 'All';
    if (hasTipFilter) {
      tipFilters = this.dropdownTipModel.map(item => item.label).join(', ');
    }

    return {
      hasFilters: hasSearchFilter || hasTypeFilter || hasTipFilter,
      searchTerm: this.searchTerm.trim(),
      typeFilters: typeFilters,
      tipFilters: tipFilters,
      totalEntries: this.auditLogEntries.length,
      filteredEntries: this.getFilteredData().length
    };
  }

  cancel() {
    this.activeModal.dismiss();
  }
}