import {ChangeDetectorRef, Component, Input, OnInit, inject} from "@angular/core";
import {NgForm, FormsModule} from "@angular/forms";
import {Constants} from "@app/shared/constants/constants";
import {HttpService} from "@app/shared/services/http.service";
import {NgbDate, NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {DatePipe, NgClass} from "@angular/common";
import {StatisticalReportsResolver} from "@app/shared/resolvers/statistical-reports.resolver";
import {StatisticalTemplatesResolver} from "@app/shared/resolvers/statistical-templates.resolver";
import {statisticalReportResolverModel} from "@app/models/resolvers/statistical-report-resolver-model";
import {ChannelFilterOption, DateFilter, FilterOption, FilterOptionsResponse, StatisticsFilter, statisticalTemplateResolverModel} from "@app/models/resolvers/statistical-template-resolver-model";
import {StatisticalReportEditorComponent} from "@app/pages/analyst/statistics/statistical-report-editor/statistical-report-editor.component";
import {DateRangeSelectorComponent} from "@app/shared/components/date-selector/date-selector.component";
import {IDropdownSettings, NgMultiSelectDropDownModule} from "ng-multiselect-dropdown";
import {PaginatedInterfaceComponent} from "@app/shared/components/paginated-interface/paginated-interface.component";
import {TableHeaderComponent} from "@app/shared/components/table/table-header.component";
import {TableFilterOption, TableState} from "@app/shared/components/table/table-state";
import {TranslateModule} from "@ngx-translate/core";

/** A report as the table lists it: the fields it is sorted and filtered by */
interface ReportRow {
  id: string;
  label: string;
  creation_date: string;
  template: string;
  report: statisticalReportResolverModel;
}

@Component({
    selector: "src-statistical-reports-tab",
    templateUrl: "./statistical-reports-tab.component.html",
    standalone: true,
    imports: [StatisticalReportEditorComponent, FormsModule, NgbTooltipModule, NgClass, DatePipe, DateRangeSelectorComponent, NgMultiSelectDropDownModule, PaginatedInterfaceComponent, TableHeaderComponent, TranslateModule]
})
export class StatisticalReportsTabComponent implements OnInit {
  private readonly httpService = inject(HttpService);
  private readonly reportsResolver = inject(StatisticalReportsResolver);
  private readonly templatesResolver = inject(StatisticalTemplatesResolver);
  private readonly cdr = inject(ChangeDetectorRef);
  @Input() statisticsForm!: NgForm;
  @Input() filterOptions: FilterOptionsResponse;

  reportsData: statisticalReportResolverModel[] = [];
  @Input() reportsForm!: NgForm;
  showAddReport = false;

  readonly table = new TableState<ReportRow>({
    orderBy: "creation_date",
    orderDesc: true,
    filters: {
      creation_date: {type: "daterange"},
      template: {type: "select"}
    }
  });

  templateOptions: TableFilterOption[] = [];

  /** The report whose card is open under its row */
  expandedReportId = "";

  new_report: { label: string; template_id: string; data: Record<string, unknown> } = {
    label: "",
    template_id: "",
    data: {}
  };

  channelDropdownVisible = false;
  channelDropdownModel: ChannelFilterOption[] = [];
  channelDropdownData: ChannelFilterOption[] = [];
  channelFilterActive = false;
  dateFilter: DateFilter | null = null;
  datePicker = false;
  dateModel: { fromDate: NgbDate | null; toDate: NgbDate | null } | null = null;

  channelDropdownSettings: IDropdownSettings = {
    singleSelection: false,
    idField: "id",
    textField: "label",
    selectAllText: "Select All",
    unSelectAllText: "UnSelect All",
    itemsShowLimit: 3,
    allowSearchFilter: true,
    enableCheckAll: false
  };

  protected readonly Constants = Constants;
  get templatesData(): statisticalTemplateResolverModel[] {
    return this.templatesResolver.dataModel;
  }

  /** The columns of the table, for the detail that spans them all */
  readonly columnCount = 4;

  private templateLabel(templateId: string): string {
    return this.templatesData.find(template => template.id === templateId)?.label || "";
  }

  private refreshRows(): void {
    const rows: ReportRow[] = this.reportsData.map(report => ({
      id: report.id,
      label: report.label,
      creation_date: report.creation_date,
      template: this.templateLabel(report.template_id),
      report
    }));

    this.templateOptions = [...new Set(rows.map(row => row.template).filter(label => label))]
      .sort((a, b) => a.localeCompare(b))
      .map(label => ({id: label, label}));

    this.table.setItems(rows);
  }

  onRowClick(row: ReportRow, event: Event): void {
    // The actions the row carries keep working: only the row itself opens
    if ((event.target as HTMLElement).closest("a, button, input, select, textarea, label")) {
      return;
    }

    this.toggleReport(row);
  }

  toggleReport(row: ReportRow): void {
    this.expandedReportId = this.expandedReportId === row.id ? "" : row.id;
  }

  deleteReport(row: ReportRow): void {
    this.httpService.requestDeleteStatisticalReport(row.id).subscribe({
      next: () => {
        this.onReportRemoved(row.id);
      }
    });
  }

  ngOnInit(): void {
    this.reportsData = [...this.reportsResolver.dataModel];
    this.refreshRows();
      this.httpService.requestFilterOptions().subscribe((filterOptions: FilterOptionsResponse) => {
        if (filterOptions && Array.isArray(filterOptions.channel)) {
          filterOptions.channel = filterOptions.channel.map((ch: FilterOption & { label: string | Record<string, string> }): FilterOption => ({
            id: ch.id,
            label: typeof ch.label === "object" ? ch.label["en"] || Object.values(ch.label)[0] : ch.label
          }));
        }
        this.filterOptions = filterOptions;
        this.channelDropdownData = filterOptions?.channel || [];
      });
  }

  toggleAddReport(): void {
    this.showAddReport = !this.showAddReport;
    if (!this.showAddReport) {
      this.resetObservationFilters();
    }
  }

  toggleChannelFilter(): void {
    this.channelDropdownVisible = !this.channelDropdownVisible;
    this.datePicker = false;
  }

  closeOtherDropdowns(except?: string): void {
    if (except !== "channel") {
      this.channelDropdownVisible = false;
    }

    if (except !== "date") {
      this.datePicker = false;
    }
  }

  onChannelFilterChange(): void {
    this.channelFilterActive = this.channelDropdownModel.length > 0;
  }

  onDateFilterChange(dateRange: { fromDate: string | null; toDate: string | null }): void {
    if (dateRange.fromDate && dateRange.toDate) {
      this.dateFilter = {
        fromDate: dateRange.fromDate,
        toDate: dateRange.toDate
      };
    } else {
      this.dateFilter = null;
    }
  }

  hasActiveFilters(): boolean {
    return this.channelFilterActive || this.dateFilter !== null;
  }

  getFilterTooltip(): string {
    if (this.channelDropdownModel.length === 0) {
      return "Channel";
    }

    return this.channelDropdownModel.map(item => item.label).join(", ");
  }

  getFilterDisplayText(): string {
    if (this.channelDropdownModel.length === 0) {
      return "Channel";
    }

    if (this.channelDropdownModel.length === 1) {
      return this.channelDropdownModel[0].label;
    }

    return `${this.channelDropdownModel.length} selected`;
  }

  clearObservationFilters(): void {
    this.channelDropdownModel = [];
    this.channelFilterActive = false;
    this.channelDropdownVisible = false;
    this.dateFilter = null;
    this.datePicker = false;
  }

  private resetObservationFilters(): void {
    this.clearObservationFilters();
    this.dateModel = null;
  }

  private toIsoDay(value: string): string {
    const date = new Date(value);
    return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
  }

  private buildObservation(): { filters: StatisticsFilter; channels: ChannelFilterOption[]; dateRange: DateFilter | null } {
    const filters: StatisticsFilter = {};

    if (this.dateFilter?.fromDate && this.dateFilter?.toDate) {
      // Plain dates: the backend treats date_to as inclusive of the whole day
      filters.date_from = this.toIsoDay(this.dateFilter.fromDate);
      filters.date_to = this.toIsoDay(this.dateFilter.toDate);
    }

    if (this.channelDropdownModel.length > 0) {
      filters.channel = this.channelDropdownModel.map(item => item.id || item.label);
    }

    return {
      filters,
      channels: this.channelDropdownModel.map(item => ({id: item.id, label: item.label})),
      dateRange: this.dateFilter
    };
  }

  addReport(): void {
    const observation = this.buildObservation();
    this.new_report.data = {
      filters: observation.filters,
      observation: {
        channels: observation.channels,
        dateRange: observation.dateRange
      }
    };

    this.httpService.requestCreateStatisticalReport(this.new_report).subscribe({
      next: (response) => {
        this.reportsResolver.dataModel.push(response);
        this.reportsData = [...this.reportsResolver.dataModel];
        this.refreshRows();
        this.new_report = { label: "", template_id: "", data: {} };
        this.resetObservationFilters();
        this.cdr.markForCheck();
      }
    });
  }

  onReportRemoved(reportId: string): void {
    const index = this.reportsResolver.dataModel.findIndex(report => report.id === reportId);
    if (index !== -1) {
      this.reportsResolver.dataModel.splice(index, 1);
    }

    if (this.expandedReportId === reportId) {
      this.expandedReportId = "";
    }

    this.reportsData = [...this.reportsResolver.dataModel];
    this.refreshRows();
    this.cdr.markForCheck();
  }
}
