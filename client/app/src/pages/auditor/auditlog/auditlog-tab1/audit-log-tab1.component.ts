import {Component, OnInit, inject} from "@angular/core";
import {auditlogResolverModel} from "@app/models/resolvers/auditlog-resolver-model";
import {AuditLogResolver} from "@app/shared/resolvers/audit-log-resolver.service";
import {UsersResolver} from "@app/shared/resolvers/users.resolver";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {User} from "@app/models/resolvers/user-resolver-model";
import {UtilsService} from "@app/shared/services/utils.service";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {DatePipe, NgClass} from "@angular/common";
import {FormsModule} from "@angular/forms";
import {NgbDate, NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {TranslateModule, TranslateService} from "@ngx-translate/core";
import {PaginatedInterfaceComponent} from "@app/shared/components/paginated-interface/paginated-interface.component";
import {DateRangeSelectorComponent} from "@app/shared/components/date-selector/date-selector.component";
import {IDropdownSettings, NgMultiSelectDropDownModule} from "ng-multiselect-dropdown";


@Component({
    selector: "src-auditlog-tab1",
    templateUrl: "./audit-log-tab1.component.html",
    standalone: true,
    imports: [DatePipe, DateRangeSelectorComponent, FormsModule, NgbTooltipModule, NgClass, NgMultiSelectDropDownModule, PaginatedInterfaceComponent, TranslatorPipe, TranslateModule]
})
export class AuditLogTab1Component implements OnInit {
  protected authenticationService = inject(AuthenticationService);
  private auditLogResolver = inject(AuditLogResolver);
  private usersResolver = inject(UsersResolver);
  protected nodeResolver = inject(NodeResolver);
  protected utilsService = inject(UtilsService);
  private translateService = inject(TranslateService);

  auditLog: auditlogResolverModel[] = [];
  filteredAuditLog: auditlogResolverModel[] = [];

  users: User[] = [];

  // Date filtering properties
  dateFilter: [number, number] | null = null;
  dateModel: { fromDate: NgbDate | null; toDate: NgbDate | null; } | null = null;
  datePicker: boolean = false;

  // Type filtering properties
  dropdownTypeModel: { id: number; label: string; color?: string; }[] = [];
  dropdownTypeData: { id: number; label: string; color?: string; }[] = [];
  typeDropdownVisible: boolean = false;

  // Dropdown settings
  dropdownSettings: IDropdownSettings = {
    idField: "id",
    textField: "label",
    itemsShowLimit: 3,
    selectAllText: this.translateService.instant("Select all"),
    unSelectAllText: this.translateService.instant("Deselect all")
  };

  ngOnInit() {
    this.loadUsersData();
    this.loadAuditLogData();
    this.initializeTypeFilterData();
    this.updateFilteredAuditLogData();
  }

  loadUsersData() {
    this.users = this.usersResolver.dataModel;
  }

  loadAuditLogData() {
    if (Array.isArray(this.auditLogResolver.dataModel)) {
      this.auditLog = this.auditLogResolver.dataModel;
    } else {
      this.auditLog = [this.auditLogResolver.dataModel];
    }
  }

  updateFilteredAuditLogData() {
    let filtered = this.auditLog;

    // Apply date filter
    if (this.dateFilter) {
      const [fromTime, toTime] = this.dateFilter;
      filtered = filtered.filter(item => {
        const itemTime = new Date(item.date).getTime();
        return itemTime >= fromTime && itemTime <= toTime;
      });
    }

    // Apply type filter
    if (this.dropdownTypeModel && this.dropdownTypeModel.length > 0) {
      const selectedCategories = this.dropdownTypeModel.map(item => item.label);
      filtered = filtered.filter(item => {
        const category = this.utilsService.getAuditLogCategory(item.type);
        return selectedCategories.includes(category);
      });
    }

    this.filteredAuditLog = filtered;
  }

  initializeTypeFilterData() {
    this.dropdownTypeData = [
      { id: 1, label: 'Low', color: 'info' },
      { id: 2, label: 'Medium', color: 'warning' },
      { id: 3, label: 'High', color: 'danger' }
    ];
  }

  getUserName(logType:string, userId: string): string {
    if (userId === 'system') {
      return this.translateService.instant('system');
    } else if (logType.startsWith('whistleblower')) {
      return this.translateService.instant('Whistleblower');
    }

    const user = this.users.find(u => u.id === userId);
    if (user) {
      return user.name;
    }

    // Return the ID if user not found (might be deleted user)
    return userId;
  }

  onDateFilterChange(event: { fromDate: string | null; toDate: string | null }) {
    const {fromDate, toDate} = event;
    if (!fromDate && !toDate) {
      this.dateFilter = null;
      this.datePicker = false;
    }
    if (fromDate && toDate) {
      this.dateFilter = [new Date(fromDate).getTime(), new Date(toDate).getTime()];
    }
    this.updateFilteredAuditLogData();
  }

  onTypeFilterChange(model: { id: number; label: string; }[]) {
    this.dropdownTypeModel = model;
    this.updateFilteredAuditLogData();
  }

  toggleTypeDropdown() {
    this.typeDropdownVisible = !this.typeDropdownVisible;
    this.datePicker = false;
  }

  checkTypeFilter(model: { id: number; label: string; }[]): boolean {
    return model && model.length > 0;
  }

  getTypeDotColor(type: string): string {
    const category = this.utilsService.getAuditLogCategory(type);

    switch(category) {
      case 'Low':
        return 'text-info';
      case 'Medium':
        return 'text-warning';
      case 'High':
        return 'text-danger';
      default:
        return 'text-primary';
    }
  }

  exportAuditLog() {
    this.utilsService.generateCSV('auditlog', this.auditLog, ['date', 'type', 'user_id', 'object_id', 'data']);
  }
}
