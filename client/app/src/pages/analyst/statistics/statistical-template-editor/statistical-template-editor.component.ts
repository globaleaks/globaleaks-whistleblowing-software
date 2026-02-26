import {Component, EventEmitter, Input, OnInit, Output, inject} from "@angular/core";
import {NgForm, FormsModule} from "@angular/forms";
import {NgbDropdownModule, NgbModal, NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {UtilsService} from "@app/shared/services/utils.service";
import {HttpService} from "@app/shared/services/http.service";
import {CommonModule, DatePipe} from "@angular/common";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {ChannelFilterOption, DateFilter, FilterOptionsResponse, MetricCard, MetricModalResult, statisticalTemplateResolverModel, StatisticsFilter} from "@app/models/resolvers/statistical-template-resolver-model";
import {ReportTemplateData} from "@app/models/analyst/report-template.model";
import {DateRangeSelectorComponent} from "@app/shared/components/date-selector/date-selector.component";
import {AddMetricModalComponent} from "@app/shared/modals/add-metric-modal/add-metric-modal.component";
import {ManageMetricModalComponent} from "@app/shared/modals/manage-metric-modal/manage-metric-modal.component";
import {StatisticsResolver} from "@app/shared/resolvers/statistics.resolver";
import {statisticsResolverModel} from "@app/models/resolvers/statistics-resolver-model";
import {TranslateModule} from "@ngx-translate/core";
import {IDropdownSettings, NgMultiSelectDropDownModule} from "ng-multiselect-dropdown";
import {NgbDate} from "@ng-bootstrap/ng-bootstrap";
import {provideCharts, withDefaultRegisterables} from "ng2-charts";
import {StatisticalTemplateViewComponent} from "@app/pages/analyst/statistics/statistical-template-view/statistical-template-view.component";
import {StatisticalTemplateService} from "@app/pages/analyst/statistics/statistical-template-service";

@Component({
  selector: "src-statistical-template-editor",
  templateUrl: "./statistical-template-editor.component.html",
  standalone: true,
  providers: [provideCharts(withDefaultRegisterables())],
  imports: [
    DatePipe,
    FormsModule,
    NgbTooltipModule,
    TranslatorPipe,
    CommonModule,
    TranslateModule,
    NgbDropdownModule,
    NgMultiSelectDropDownModule,
    DateRangeSelectorComponent,
    StatisticalTemplateViewComponent
  ]
})
export class StatisticalTemplateEditorComponent implements OnInit {
  private readonly httpService = inject(HttpService);
  private readonly utilsService = inject(UtilsService);
  private readonly modalService = inject(NgbModal);
  private readonly statisticsResolver = inject(StatisticsResolver);
  private readonly templateService = inject(StatisticalTemplateService);

  @Input() templateData!: statisticalTemplateResolverModel;
  @Input() templatesData: statisticalTemplateResolverModel[] = [];
  @Input() filterOptions: FilterOptionsResponse;
  @Input() index = 0;
  @Input() editTemplate!: NgForm;
  @Output() dataToParent = new EventEmitter<string>();

  editing = false;
  availableMetrics: MetricCard[] = [];
  metricCards: MetricCard[] = [];
  chartMetrics: MetricCard[] = [];

  channelDropdownVisible = false;
  channelDropdownModel: ChannelFilterOption[] = [];
  channelDropdownData: ChannelFilterOption[] = [];
  channelFilterActive = false;
  dateFilter: DateFilter | null = null;
  datePicker = false;
  dateModel: { fromDate: NgbDate | null; toDate: NgbDate | null } | null = null;
  currentFilteredData: statisticsResolverModel | null = null;
  currentTemplate: ReportTemplateData | null = null;
  filterRevision = 0;

  private filterRequestId = 0;
  private baseStatisticsData: statisticsResolverModel | null = null;

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

  ngOnInit(): void {
    this.initializeComponentWithTemplate(this.templateData);
  }

  private initializeComponentWithTemplate(template: statisticalTemplateResolverModel): void {
    this.baseStatisticsData = this.statisticsResolver.dataModel ? {...this.statisticsResolver.dataModel} : null;
    this.initializeFilters();
    this.initializeMetrics();
    this.loadTemplateConfiguration(template);
    this.saveSelectedMetrics();
  }

  private loadTemplateConfiguration(template: statisticalTemplateResolverModel): void {
    const cfg = this.templateService.loadTemplateConfiguration(template, this.availableMetrics);
    this.metricCards = cfg.metricCards;
    this.chartMetrics = cfg.chartMetrics;
  }

  private getFilteredStatistics(): statisticsResolverModel | null {
    return this.currentFilteredData || this.statisticsResolver.dataModel || null;
  }

  private initializeMetrics(): void {
    const dataModel = this.getFilteredStatistics();
    if (!dataModel) {
      this.availableMetrics = [];
      return;
    }

    this.availableMetrics = this.templateService.createMetricCatalog(dataModel);
  }

  private initializeFilters() {
    this.channelDropdownData = this.filterOptions?.channel || [];
  }

  toggleChannelFilter(): void {
    this.channelDropdownVisible = !this.channelDropdownVisible;
    this.datePicker = false;
  }

  onChannelFilterChange(): void {
    this.channelFilterActive = this.channelDropdownModel.length > 0;
    this.applyFilters();
  }

  clearAllFilters(): void {
    this.channelDropdownModel = [];
    this.channelFilterActive = false;
    this.channelDropdownVisible = false;
    this.dateFilter = null;
    this.datePicker = false;
    this.currentFilteredData = null;

    if (this.baseStatisticsData) {
      this.statisticsResolver.dataModel = {...this.baseStatisticsData};
    }

    this.initializeMetrics();
    this.triggerViewRefresh();
  }

  closeOtherDropdowns(except?: string): void {
    if (except !== "channel") {
      this.channelDropdownVisible = false;
    }

    if (except !== "date") {
      this.datePicker = false;
    }
  }

  getFilterTooltip(filterType: string): string {
    if (filterType !== "channel") {
      return "";
    }

    if (this.channelDropdownModel.length === 0) {
      return "Channel";
    }

    return this.channelDropdownModel.map(item => item.label).join(", ");
  }

  getFilterDisplayText(filterType: string): string {
    if (filterType !== "channel") {
      return "Unknown";
    }

    if (this.channelDropdownModel.length === 0) {
      return "Channel";
    }

    if (this.channelDropdownModel.length === 1) {
      return this.channelDropdownModel[0].label;
    }

    return `${this.channelDropdownModel.length} selected`;
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

    this.applyFilters();
  }

  hasActiveFilters(): boolean {
    return this.channelFilterActive || this.dateFilter !== null;
  }

  private applyFilters(): void {
    const filters: StatisticsFilter = {};

    if (this.dateFilter?.fromDate && this.dateFilter?.toDate) {
      filters.date_from = new Date(this.dateFilter.fromDate).getTime();
      filters.date_to = new Date(this.dateFilter.toDate).getTime();
    }

    if (this.channelDropdownModel.length > 0) {
      filters.channel = this.channelDropdownModel.map(item => item.id || item.label);
    }

    if (!Object.keys(filters).length) {
      this.currentFilteredData = null;
      if (this.baseStatisticsData) {
        this.statisticsResolver.dataModel = {...this.baseStatisticsData};
      }
      this.initializeMetrics();
      this.triggerViewRefresh();
      return;
    }

    const requestId = ++this.filterRequestId;
    this.httpService.requestStatisticsResource(filters).subscribe({
      next: (filteredData: statisticsResolverModel) => {
        if (requestId !== this.filterRequestId) {
          return;
        }

        this.currentFilteredData = filteredData;
        this.statisticsResolver.dataModel = filteredData;
        this.initializeMetrics();
        this.triggerViewRefresh();
      }
    });
  }

  private triggerViewRefresh(): void {
    this.filterRevision += 1;
    this.templateData = {...this.templateData};
  }

  addNewMetric(): void {
    const currentCardIds = this.metricCards.map(card => card.id);
    const currentChartIds = this.chartMetrics.map(chart => chart.id);
    const allCurrentIds = [...currentCardIds, ...currentChartIds];

    const modalRef = this.modalService.open(AddMetricModalComponent, {
      size: "lg",
      backdrop: "static",
      keyboard: false
    });

    modalRef.componentInstance.availableMetrics = this.availableMetrics;
    modalRef.componentInstance.currentMetricIds = allCurrentIds;

    modalRef.result.then((result: MetricModalResult & { displayType?: "card" | "chart" }) => {
      if (!result?.metric) {
        return;
      }

      const newMetricCard: MetricCard = {
        id: result.metric.id,
        title: result.metric.title,
        value: result.metric.value,
        chartType: result.chartType,
        category: result.metric.category,
        compatibleTypes: result.metric.compatibleTypes
      };

      if (["bar", "pie"].includes(result.chartType)) {
        this.chartMetrics.push(newMetricCard);
      } else {
        this.metricCards.push(newMetricCard);
      }

      this.saveSelectedMetrics();
    });
  }

  removeMetric(metricId: string): void {
    this.metricCards = this.metricCards.filter(card => card.id !== metricId);
    const chartMetricIndex = this.chartMetrics.findIndex(chart => chart.id === metricId);
    if (chartMetricIndex !== -1) {
      this.chartMetrics.splice(chartMetricIndex, 1);
    }

    this.saveSelectedMetrics();
  }

  canAddMoreMetrics(): boolean {
    const currentCardIds = this.metricCards.map(card => card.id);
    const currentChartIds = this.chartMetrics.map(chart => chart.id);
    const allCurrentIds = [...currentCardIds, ...currentChartIds];
    const availableToAdd = this.availableMetrics.filter(metric => !allCurrentIds.includes(metric.id));

    return availableToAdd.length > 0;
  }

  manageMetric(metricId: string): void {
    let currentItem = this.metricCards.find(card => card.id === metricId);
    let isChart = false;

    if (!currentItem) {
      currentItem = this.chartMetrics.find(chart => chart.id === metricId);
      isChart = true;
    }

    if (!currentItem) {
      return;
    }

    const allCurrentIds = [...this.metricCards.map(card => card.id), ...this.chartMetrics.map(chart => chart.id)];

    const modalRef = this.modalService.open(ManageMetricModalComponent, {
      size: "lg",
      backdrop: "static",
      keyboard: false
    });

    modalRef.componentInstance.availableMetrics = this.availableMetrics;
    modalRef.componentInstance.currentMetricIds = allCurrentIds;
    modalRef.componentInstance.currentMetricCard = currentItem;

    modalRef.result.then((result: MetricModalResult) => {
      if (!result?.metric) {
        return;
      }

      const newMetricItem: MetricCard = {
        id: result.metric.id,
        title: result.metric.title,
        value: result.metric.value,
        chartType: result.chartType,
        category: result.metric.category,
        compatibleTypes: result.metric.compatibleTypes
      };

      if (isChart) {
        this.chartMetrics = this.chartMetrics.filter(chart => chart.id !== metricId);
      } else {
        this.metricCards = this.metricCards.filter(card => card.id !== metricId);
      }

      if (["bar", "pie"].includes(result.chartType)) {
        this.chartMetrics.push(newMetricItem);
      } else {
        this.metricCards.push(newMetricItem);
      }

      this.saveSelectedMetrics();
    });
  }

  private buildTemplateData(): ReportTemplateData {
    const existingData = (this.templateData.data || {}) as Partial<ReportTemplateData> & { config?: any };
    const existingConfig = existingData.config || {};

    return {
      ...existingData,
      config: {
        ...existingConfig,
        selectedMetrics: this.metricCards.map(card => ({
          id: card.id,
          title: card.title
        })),
        selectedCharts: this.chartMetrics.map(chart => ({
          id: chart.id,
          title: chart.title,
          chartType: chart.chartType
        }))
      }
    } as ReportTemplateData;
  }

  private saveSelectedMetrics(): void {
    const selectedCardIds = this.metricCards.map(card => card.id);
    const selectedChartIds = this.chartMetrics.map(card => ({id: card.id, chartType: card.chartType}));
    localStorage.setItem("selected_metrics", JSON.stringify(selectedCardIds));
    localStorage.setItem("selected_chart_metrics", JSON.stringify(selectedChartIds));

    this.currentTemplate = this.buildTemplateData();
    this.templateData.data = this.currentTemplate;
    this.templateData = {...this.templateData};
  }

  toggleEditing(): void {
    this.editing = !this.editing;
  }

  deleteTemplate(template: statisticalTemplateResolverModel): void {
    this.httpService.requestDeleteStatisticalTemplate(template.id).subscribe({
      next: () => {
        this.dataToParent.emit();
        this.utilsService.deleteResource(this.templatesData, template);
      }
    });
  }

  saveTemplate(template: statisticalTemplateResolverModel): void {
    template.data = this.currentTemplate || this.buildTemplateData();
    this.httpService.requestUpdateStatisticalTemplate(template.id, template).subscribe({
      next: (updatedTemplate: statisticalTemplateResolverModel) => {
        this.templateData = updatedTemplate;
        this.currentTemplate = updatedTemplate.data as ReportTemplateData;

        const templateIndex = this.templatesData.findIndex(item => item.id === updatedTemplate.id);
        if (templateIndex !== -1) {
          this.templatesData[templateIndex] = updatedTemplate;
        }
      }
    });
  }
}
