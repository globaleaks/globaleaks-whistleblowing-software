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
import {TranslateModule} from "@ngx-translate/core";

@Component({
    selector: "src-statistical-reports-tab",
    templateUrl: "./statistical-reports-tab.component.html",
    standalone: true,
    imports: [StatisticalReportEditorComponent, FormsModule, NgbTooltipModule, NgClass, DatePipe, DateRangeSelectorComponent, NgMultiSelectDropDownModule, PaginatedInterfaceComponent, TranslateModule]
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
  new_report: { label: string; template_id: string; data: Record<string, unknown> } = {
    label: "",
    template_id: "",
    data: {}
  };
  realtime = false;

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

  ngOnInit(): void {
    this.reportsData = this.sortReports(this.reportsResolver.dataModel);
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
    this.realtime = false;
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
      realtime: this.realtime,
      filters: observation.filters,
      observation: {
        channels: observation.channels,
        dateRange: observation.dateRange
      }
    };

    this.httpService.requestCreateStatisticalReport(this.new_report).subscribe({
      next: (response) => {
        this.reportsResolver.dataModel.push(response);
        this.reportsData = this.sortReports(this.reportsResolver.dataModel);
        this.new_report = { label: "", template_id: "", data: {} };
        this.realtime = false;
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
    this.reportsData = this.sortReports(this.reportsResolver.dataModel);
    this.cdr.markForCheck();
  }

  private sortReports(reports: statisticalReportResolverModel[]): statisticalReportResolverModel[] {
    // Realtime reports first, then non-realtime; within each group most
    // recent first by creation date.
    return [...reports].sort((a, b) => {
      const aRank = a.data?.realtime ? 0 : 1;
      const bRank = b.data?.realtime ? 0 : 1;
      if (aRank !== bRank) {
        return aRank - bRank;
      }
      return (b.creation_date || "").localeCompare(a.creation_date || "");
    });
  }
}
