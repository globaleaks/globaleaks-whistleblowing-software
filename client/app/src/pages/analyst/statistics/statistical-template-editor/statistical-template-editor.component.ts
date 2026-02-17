import {Component, EventEmitter, Input, OnInit, Output, inject} from "@angular/core";
import {NgForm, FormsModule} from "@angular/forms";
import {NgbDropdownModule, NgbModal, NgbTooltipModule } from "@ng-bootstrap/ng-bootstrap";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {UtilsService} from "@app/shared/services/utils.service";
import {HttpService} from "@app/shared/services/http.service";
import {nodeResolverModel} from "@app/models/resolvers/node-resolver-model";
import {CommonModule, DatePipe, NgClass} from "@angular/common";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {FilterPipe} from "@app/shared/pipes/filter.pipe";
import {ChartConfig, MetricCard, statisticalTemplateResolverModel} from "@app/models/resolvers/statistical-template-resolver-model";
import {ReportTemplate} from "@app/models/analyst/report-template.model";
import {DateRangeSelectorComponent} from "@app/shared/components/date-selector/date-selector.component";
import {AddMetricModalComponent} from "@app/shared/modals/add-metric-modal/add-metric-modal.component";
import {ManageMetricModalComponent} from "@app/shared/modals/manage-metric-modal/manage-metric-modal.component";
import {StatisticsResolver} from "@app/shared/resolvers/statistics.resolver";
import {TranslateModule} from "@ngx-translate/core";
import {NgMultiSelectDropDownModule} from "ng-multiselect-dropdown";
import {provideCharts, withDefaultRegisterables, BaseChartDirective} from "ng2-charts";

@Component({
  selector: "src-statistical-template-editor",
  templateUrl: "./statistical-template-editor.component.html",
  standalone: true,
  providers: [provideCharts(withDefaultRegisterables())],
  imports: [DatePipe, FormsModule, NgbTooltipModule, NgClass, TranslatorPipe, FilterPipe,
    CommonModule,
    TranslateModule,
    NgbDropdownModule,
    NgMultiSelectDropDownModule,
    DateRangeSelectorComponent,
    BaseChartDirective
  ]
})
export class StatisticalTemplateEditorComponent implements OnInit {
  private httpService = inject(HttpService);
  protected nodeResolver = inject(NodeResolver);
  private utilsService = inject(UtilsService);
  private modalService = inject(NgbModal);
  private statisticsResolver = inject(StatisticsResolver);
  @Input() templateData: statisticalTemplateResolverModel;
  @Input() templatesData: statisticalTemplateResolverModel[];
  @Input() filterOptions: any;
  @Input() index: number;
  @Input() editTemplate: NgForm;
  @Output() dataToParent = new EventEmitter<string>();
  editing = false;
  nodeData: nodeResolverModel;

  chartConfigs: ChartConfig[] = [];
  availableMetrics: MetricCard[] = [];
  metricCards: MetricCard[] = [];
  chartMetrics: MetricCard[] = [];

  private readonly GLOBALEAKS_COLORS = [
    '#3679BB',
    '#205282',
    '#9FC9F1',
    '#103253',
    '#4BC0C0',
    '#FFCE56',
    '#36A2EB',
    '#5A9FD4'
  ];

  statusDropdownVisible = false;
  tagDropdownVisible = false;
  tenantDropdownVisible = false;
  channelDropdownVisible = false;
  statusDropdownModel: any[] = [];
  tagDropdownModel: any[] = [];
  tenantDropdownModel: any[] = [];
  channelDropdownModel: any[] = [];
  statusDropdownData: any[] = [];
  tagDropdownData: any[] = [];
  tenantDropdownData: any[] = [];
  channelDropdownData: any[] = [];
  statusFilterActive = false;
  tagFilterActive = false;
  tenantFilterActive = false;
  channelFilterActive = false;
  dateFilter: { fromDate: string, toDate: string } | null = null;
  datePicker = false;
  dateModel: any = null;
  currentFilteredData: any = null;
  currentTemplate: any = null;

  dropdownSettings = {
    singleSelection: false,
    idField: 'id',
    textField: 'label',
    selectAllText: 'Select All',
    unSelectAllText: 'UnSelect All',
    itemsShowLimit: 3,
    allowSearchFilter: true,
    enableCheckAll: false
  };

  compactDropdownSettings = {
    singleSelection: false,
    idField: 'id',
    textField: 'label',
    selectAllText: 'All',
    unSelectAllText: 'None',
    itemsShowLimit: 2,
    allowSearchFilter: false,
    noDataAvailablePlaceholderText: 'No data available',
    closeDropDownOnSelection: false
  };

  statusDropdownSettings = {
    singleSelection: false,
    idField: 'id',
    textField: 'label',
    selectAllText: 'Select All',
    unSelectAllText: 'UnSelect All',
    itemsShowLimit: 3,
    allowSearchFilter: true,
    enableCheckAll: false
  };

  tagDropdownSettings = {
    singleSelection: false,
    idField: 'id',
    textField: 'label',
    selectAllText: 'Select All',
    unSelectAllText: 'UnSelect All',
    itemsShowLimit: 3,
    allowSearchFilter: true,
    enableCheckAll: false
  };

  tenantDropdownSettings = {
    singleSelection: false,
    idField: 'id',
    textField: 'label',
    selectAllText: 'Select All',
    unSelectAllText: 'UnSelect All',
    itemsShowLimit: 3,
    allowSearchFilter: true,
    enableCheckAll: false
  };

  channelDropdownSettings = {
    singleSelection: false,
    idField: 'id',
    textField: 'label',
    selectAllText: 'Select All',
    unSelectAllText: 'UnSelect All',
    itemsShowLimit: 3,
    allowSearchFilter: true,
    enableCheckAll: false
  };

  ngOnInit(): void {
    this.nodeData = this.nodeResolver.dataModel;
    this.initializeComponentWithTemplate(this.templateData);

  }

  private loadTemplateConfiguration(template: ReportTemplate): void {
    this.metricCards = [];
    this.chartMetrics = [];
    const selectedMetrics: any[] = (template.data.config && (template.data.config as any).selectedMetrics) ? (template.data.config as any).selectedMetrics : [];
    if (selectedMetrics && selectedMetrics.length > 0) {
      const templateMetrics = selectedMetrics
        .map(metricItem => {
          const metricId = typeof metricItem === 'string' ? metricItem : metricItem.id;
          return this.availableMetrics.find(m => m.id === metricId);
        })
        .filter((m): m is MetricCard => !!m);
      this.metricCards = templateMetrics.map(metric => ({
        ...metric,
        chartType: metric.chartType || 'number'
      }));
    }

    if (this.metricCards.length === 0) {

      if (this.availableMetrics.length >= 3) {
        this.metricCards = this.availableMetrics.slice(0, 3).map(metric => ({
          ...metric,
          chartType: 'number'
        }));

      }
    }

    const selectedCharts: any[] = (template.data.config && (template.data.config as any).selectedCharts) ? (template.data.config as any).selectedCharts : [];

    if (selectedCharts && selectedCharts.length > 0) {
      const templateCharts = selectedCharts
        .map(chartItem => {
          const chartId = typeof chartItem === 'string' ? chartItem : chartItem.id;
          const chartType = typeof chartItem === 'string' ? 'pie' : (chartItem.chartType || 'pie');
          const found = this.availableMetrics.find(m => m.id === chartId);
          return found ? { ...found, chartType } : null;
        })
        .filter((m): m is MetricCard & { chartType: string } => !!m);

      this.chartMetrics = templateCharts;
    }
  }

  private initializeComponentWithTemplate(template: any): void {
    this.initializeFilters();
    this.initializeMetrics();
    this.loadTemplateConfiguration(template);
    this.initializeCharts();
    this.saveSelectedMetrics();
  }

  private getFilteredStatistics() {
    return this.currentFilteredData || this.statisticsResolver.dataModel;
  }

  private initializeCharts(): void {
    this.updateChartConfigs();
  }

  private getMetricCompatibility(metricId: string): { category: 'numeric' | 'comparative' | 'distribution', compatibleTypes: string[] } {
    const numericOnlyMetrics = [
      'reports_received', 'avg_access_time', 'avg_response_time', 'avg_disclosure_time',
      'avg_exchanges', 'total_exchanges', 'reports_with_exchanges', 'security_usage'
    ];

    const comparativeMetrics = [
      'reports_accessed', 'reports_not_accessed', 'anonymous_reports', 'subscribed_reports',
      'initially_anonymous_reports', 'tor_reports', 'direct_reports', 'mobile_reports',
      'desktop_reports', 'disclosure_rate'
    ];

    const distributionMetrics = [
      'reports_anonymous_vs_identified', 'reports_access_status', 'reports_platform_distribution'
    ];

    if (numericOnlyMetrics.includes(metricId)) {
      return {
        category: 'numeric',
        compatibleTypes: ['number', 'percentage']
      };
    } else if (comparativeMetrics.includes(metricId)) {
      return {
        category: 'comparative',
        compatibleTypes: ['number', 'percentage', 'pie']
      };
    } else if (distributionMetrics.includes(metricId)) {
      return {
        category: 'distribution',
        compatibleTypes: ['number', 'bar', 'pie']
      };
    } else {
      return {
        category: 'numeric',
        compatibleTypes: ['number', 'percentage']
      };
    }
  }

  private initializeMetrics(): void {
    const dataModel = this.getFilteredStatistics();

    if (!dataModel) {
      this.availableMetrics = [];
      return;
    }
    this.createMetricsFromData(dataModel);
  }

  private createMetricsFromData(dataModel: any): void {

    const reports_count = dataModel.reports_count || 0;
    const reports_with_no_access = dataModel.reports_with_no_access || 0;
    const reports_anonymous = dataModel.reports_anonymous || 0;
    const reports_subscribed = dataModel.reports_subscribed || 0;
    const reports_initially_anonymous = dataModel.reports_initially_anonymous || 0;
    const reports_mobile = dataModel.reports_mobile || 0;
    const reports_tor = dataModel.reports_tor || 0;

    const reports_accessed = reports_count - reports_with_no_access;
    const mobile_reports = reports_mobile;
    const tor_reports = reports_tor;
    const subscribed_reports = reports_subscribed;
    const initially_anonymous_reports = reports_initially_anonymous;
    const anonymous_reports = reports_anonymous;
    const reports_desktop = reports_count - mobile_reports;
    const reports_direct = reports_count - tor_reports;

    const disclosure_rate = reports_count > 0 ? ((subscribed_reports + initially_anonymous_reports) / reports_count * 100).toFixed(1) : 0;
    const access_rate = reports_count > 0 ? (reports_accessed / reports_count * 100).toFixed(1) : 0;
    const anonymity_rate = reports_count > 0 ? (anonymous_reports / reports_count * 100).toFixed(1) : 0;
    const tor_usage_rate = reports_count > 0 ? (tor_reports / reports_count * 100).toFixed(1) : 0;
    const mobile_usage_rate = reports_count > 0 ? (mobile_reports / reports_count * 100).toFixed(1) : 0;
    const later_disclosure_rate = reports_count > 0 ? (initially_anonymous_reports / reports_count * 100).toFixed(1) : 0;

    const createMetric = (id: string, title: string, value: number | string): MetricCard => {
      const compatibility = this.getMetricCompatibility(id);
      return {
        id,
        title,
        value,
        category: compatibility.category,
        compatibleTypes: compatibility.compatibleTypes
      };
    };

    const newCatalog: MetricCard[] = [
      createMetric('reports_received', 'Total Reports', reports_count),
      createMetric('reports_accessed', 'Accessed Reports', `${reports_accessed} (${access_rate}%)`),
      createMetric('reports_not_accessed', 'Unaccessed Reports', `${reports_with_no_access} (${(100 - parseFloat(access_rate.toString())).toFixed(1)}%)`),
      createMetric('anonymous_reports', 'Anonymous Reports', `${anonymous_reports} (${anonymity_rate}%)`),
      createMetric('subscribed_reports', 'Subscribed Reports', `${subscribed_reports} (${reports_count > 0 ? (subscribed_reports / reports_count * 100).toFixed(1) : 0}%)`),
      createMetric('initially_anonymous_reports', 'Later Disclosed Identity', `${initially_anonymous_reports} (${later_disclosure_rate}%)`),
      createMetric('tor_reports', 'Tor Reports', `${tor_reports} (${tor_usage_rate}%)`),
      createMetric('direct_reports', 'Direct Connection', `${reports_direct} (${(100 - parseFloat(tor_usage_rate.toString())).toFixed(1)}%)`),
      createMetric('mobile_reports', 'Mobile Reports', `${mobile_reports} (${mobile_usage_rate}%)`),
      createMetric('desktop_reports', 'Desktop Reports', `${reports_desktop} (${(100 - parseFloat(mobile_usage_rate.toString())).toFixed(1)}%)`),
      createMetric('disclosure_rate', 'Identity Disclosure Rate', `${disclosure_rate}%`),
      createMetric('security_usage', 'High Security Reports', `${tor_reports + anonymous_reports}`),
      createMetric('avg_access_time', 'Average Access Time', `${dataModel.avg_access_time_hours}h`),
      createMetric('avg_response_time', 'Average Response Time', `${dataModel.avg_response_time_hours}h`),
      createMetric('avg_disclosure_time', 'Average Identity Disclosure Time', `${dataModel.avg_identity_disclosure_time_hours}h`),
      createMetric('avg_exchanges', 'Average Exchanges per Report', dataModel.avg_exchanges_per_report.toFixed(1)),
      createMetric('total_exchanges', 'Total Exchanges', dataModel.total_exchanges || 0),
      createMetric('reports_with_exchanges', 'Reports with Exchanges', dataModel.reports_with_exchanges || 0),
      createMetric('reports_anonymous_vs_identified', 'Anonymous vs Identified Reports', `${reports_anonymous}/${reports_count - reports_anonymous}`),
      createMetric('reports_access_status', 'Access Status Distribution', `${reports_count - reports_with_no_access}/${reports_with_no_access}`),
      createMetric('reports_platform_distribution', 'Platform Distribution', `Mobile: ${reports_mobile}, Web: ${reports_count - reports_mobile - reports_tor}, Tor: ${reports_tor}`)
    ];

    if (this.availableMetrics.length === 0) {
      this.availableMetrics = newCatalog;
    } else {
      this.availableMetrics = this.availableMetrics.map(existing => newCatalog.find(n => n.id === existing.id) || existing);
    }

    this.updateMetricCardsData();
  }

  private updateMetricCardsData(): void {
    this.metricCards = this.metricCards.map(displayedCard => {
      const updatedMetric = this.availableMetrics.find(metric => metric.id === displayedCard.id);
      return updatedMetric || displayedCard;
    });
  }

  private initializeFilters() {
    this.statusDropdownData = this.filterOptions?.status || [];
    this.tenantDropdownData = this.filterOptions?.tenant || [];
    this.channelDropdownData = this.filterOptions?.channel || [];
  }

  toggleStatusFilter(): void {
    this.statusDropdownVisible = !this.statusDropdownVisible;
    this.tagDropdownVisible = false;
    this.tenantDropdownVisible = false;
    this.channelDropdownVisible = false;
    this.datePicker = false;
  }

  toggleTagFilter(): void {
    this.tagDropdownVisible = !this.tagDropdownVisible;
    this.statusDropdownVisible = false;
    this.tenantDropdownVisible = false;
    this.channelDropdownVisible = false;
    this.datePicker = false;
  }

  toggleTenantFilter(): void {
    this.tenantDropdownVisible = !this.tenantDropdownVisible;
    this.statusDropdownVisible = false;
    this.tagDropdownVisible = false;
    this.channelDropdownVisible = false;
    this.datePicker = false;
  }

  toggleChannelFilter(): void {
    this.channelDropdownVisible = !this.channelDropdownVisible;
    this.statusDropdownVisible = false;
    this.tagDropdownVisible = false;
    this.tenantDropdownVisible = false;
    this.datePicker = false;
  }

  onStatusFilterChange(): void {
    this.statusFilterActive = this.statusDropdownModel.length > 0;
    this.applyFilters();
  }

  onTagFilterChange(): void {
    this.tagFilterActive = this.tagDropdownModel.length > 0;
    this.applyFilters();
  }

  onTenantFilterChange(): void {
    this.tenantFilterActive = this.tenantDropdownModel.length > 0;
    this.applyFilters();
  }

  onChannelFilterChange(): void {
    this.channelFilterActive = this.channelDropdownModel.length > 0;
    this.applyFilters();
  }

  onDateRangeSelected(dateRange: [number, number] | null): void {
    if (dateRange && dateRange.length === 2) {
      const fromDate = new Date(dateRange[0]).toISOString().split('T')[0];
      const toDate = new Date(dateRange[1]).toISOString().split('T')[0];
      this.dateFilter = { fromDate, toDate };
    } else {
      this.dateFilter = null;
    }
    this.applyFilters();
  }

  clearAllFilters(): void {
    this.statusDropdownModel = [];
    this.tagDropdownModel = [];
    this.tenantDropdownModel = [];
    this.channelDropdownModel = [];
    this.statusFilterActive = false;
    this.tagFilterActive = false;
    this.tenantFilterActive = false;
    this.channelFilterActive = false;
    this.statusDropdownVisible = false;
    this.tagDropdownVisible = false;
    this.tenantDropdownVisible = false;
    this.channelDropdownVisible = false;
    this.dateFilter = null;
    this.datePicker = false;
    this.currentFilteredData = null;

    this.initializeMetrics();
    this.initializeCharts();
  }

  closeOtherDropdowns(except?: string): void {
    if (except !== 'status') this.statusDropdownVisible = false;
    if (except !== 'tenant') this.tenantDropdownVisible = false;
    if (except !== 'channel') this.channelDropdownVisible = false;
    if (except !== 'date') this.datePicker = false;
  }

  getFilterTooltip(filterType: string): string {
    switch (filterType) {
      case 'status':
        if (this.statusDropdownModel.length === 0) return 'Any Status';
        return this.statusDropdownModel.map(item => item.label).join(', ');
      case 'tenant':
        if (this.tenantDropdownModel.length === 0) return 'Any Tenant';
        return this.tenantDropdownModel.map(item => item.label).join(', ');
      case 'channel':
        if (this.channelDropdownModel.length === 0) return 'Any Channel';
        return this.channelDropdownModel.map(item => item.label).join(', ');
      default:
        return '';
    }
  }

  getFilterDisplayText(filterType: string): string {
    switch (filterType) {
      case 'status':
        if (this.statusDropdownModel.length === 0) return 'Any Status';
        if (this.statusDropdownModel.length === 1) return this.statusDropdownModel[0].label;
        return `${this.statusDropdownModel.length} selected`;
      case 'tenant':
        if (this.tenantDropdownModel.length === 0) return 'Any Tenant';
        if (this.tenantDropdownModel.length === 1) return this.tenantDropdownModel[0].label;
        return `${this.tenantDropdownModel.length} selected`;
      case 'channel':
        if (this.channelDropdownModel.length === 0) return 'Any Channel';
        if (this.channelDropdownModel.length === 1) return this.channelDropdownModel[0].label;
        return `${this.channelDropdownModel.length} selected`;
      default:
        return 'Unknown';
    }
  }

  onDocumentClick(event: Event): void {
    const target = event.target as Element;
    if (!target.closest('.filter-dropdown-container')) {
      this.statusDropdownVisible = false;
      this.tagDropdownVisible = false;
      this.tenantDropdownVisible = false;
      this.channelDropdownVisible = false;
    }
    if (!target.closest('.date-picker-container') && !target.closest('.fa-calendar')) {
      this.datePicker = false;
    }
  }

  onDateFilterChange(dateRange: { fromDate: string | null; toDate: string | null }): void {
    if (dateRange.fromDate && dateRange.toDate) {
      this.dateFilter = {
        fromDate: dateRange.fromDate,
        toDate: dateRange.toDate
      };
      this.applyFilters();
    } else {
      this.dateFilter = null;
      this.applyFilters();
    }
  }

  hasActiveFilters(): boolean {
    return this.statusFilterActive ||
      this.tagFilterActive ||
      this.tenantFilterActive ||
      this.channelFilterActive ||
      this.dateFilter !== null;
  }

  get charts(): ChartConfig[] {
    return this.chartConfigs;
  }

  private applyFilters(): void {
    const filters: any = {};

    if (this.dateFilter && this.dateFilter.fromDate && this.dateFilter.toDate) {
      filters.date_from = new Date(this.dateFilter.fromDate).getTime();
      filters.date_to = new Date(this.dateFilter.toDate).getTime();
    }

    if (this.statusDropdownModel && this.statusDropdownModel.length > 0) {
      filters.status = this.statusDropdownModel.map(item => item.label);
    }

    if (this.tenantDropdownModel && this.tenantDropdownModel.length > 0) {
      filters.tenant = this.tenantDropdownModel.map(item => item.label);
    }

    if (this.channelDropdownModel && this.channelDropdownModel.length > 0) {
      filters.channel = this.channelDropdownModel.map(item => item.label);
    }

    this.httpService.requestStatisticsResource(filters).subscribe({
      next: (filteredData) => {
        this.currentFilteredData = filteredData;
        this.statisticsResolver.dataModel = filteredData;
        this.initializeMetrics();
        this.initializeCharts();
      }
    });
  }

  addNewMetric(): void {
    const currentCardIds = this.metricCards.map(card => card.id);
    const currentChartIds = this.chartMetrics.map(chart => chart.id);
    const allCurrentIds = [...currentCardIds, ...currentChartIds];

    const modalRef = this.modalService.open(AddMetricModalComponent, {
      size: 'lg',
      backdrop: 'static',
      keyboard: false
    });

    modalRef.componentInstance.availableMetrics = this.availableMetrics;
    modalRef.componentInstance.currentMetricIds = allCurrentIds;

    modalRef.result.then((result: { metric: any, chartType: string, displayType: 'card' | 'chart' }) => {
      if (result && result.metric) {
        const newMetricCard: MetricCard = {
          id: result.metric.id,
          title: result.metric.title,
          value: result.metric.value,
          chartType: result.chartType,
          category: result.metric.category,
          compatibleTypes: result.metric.compatibleTypes
        };
        const isChart = ['bar', 'pie'].includes(result.chartType);
        if (isChart) {
          this.chartMetrics.push(newMetricCard);
        } else {
          this.metricCards.push(newMetricCard);
        }
        this.updateChartConfigs();
        this.saveSelectedMetrics();
      }
    })
  }

  removeMetric(metricId: string): void {
    this.metricCards = this.metricCards.filter(card => card.id !== metricId);
    this.saveSelectedMetrics();
  }

  removeChartMetric(metricId: string): void {
    this.chartMetrics = this.chartMetrics.filter(chart => chart.id !== metricId);
    this.updateChartConfigs();
    this.saveSelectedMetrics();
  }

  getMetricIdFromChartId(chartId: string): string {
    return chartId.replace('chart-', '');
  }

  private updateChartConfigs(): void {
    this.chartConfigs = [];

    this.chartMetrics.forEach((chartMetric, index) => {
      const chartConfig: ChartConfig = {
        id: `chart-${chartMetric.id}`,
        title: chartMetric.title,
        type: this.getChartType(chartMetric.chartType),
        data: this.generateChartData(chartMetric),
        options: this.getChartOptions(chartMetric.chartType)
      };
      this.chartConfigs.push(chartConfig);
    });
  }

  private getChartType(chartType?: string): 'bar' | 'pie' | 'line' {
    switch (chartType) {
      case 'bar': return 'bar';
      case 'pie': return 'pie';
      case 'line': return 'line';
      default: return 'pie';
    }
  }

  private generateChartData(metric: MetricCard): any {
    const dataModel = this.getFilteredStatistics();
    if (!dataModel) return { labels: [], datasets: [] };

    switch (metric.id) {
      case 'reports_anonymous_vs_identified':
        return {
          labels: ['Anonymous', 'Identified'],
          datasets: [{
            data: [dataModel.reports_anonymous || 0, (dataModel.reports_count || 0) - (dataModel.reports_anonymous || 0)],
            backgroundColor: [this.GLOBALEAKS_COLORS[2], this.GLOBALEAKS_COLORS[0]]
          }]
        };
      case 'reports_access_status':
        return {
          labels: ['Accessed', 'Not Accessed'],
          datasets: [{
            data: [(dataModel.reports_count || 0) - (dataModel.reports_with_no_access || 0), dataModel.reports_with_no_access || 0],
            backgroundColor: [this.GLOBALEAKS_COLORS[4], this.GLOBALEAKS_COLORS[1]]
          }]
        };
      case 'reports_platform_distribution':
        return {
          labels: ['Mobile', 'Web', 'Tor'],
          datasets: [{
            data: [dataModel.reports_mobile || 0, (dataModel.reports_count || 0) - (dataModel.reports_mobile || 0) - (dataModel.reports_tor || 0), dataModel.reports_tor || 0],
            backgroundColor: [this.GLOBALEAKS_COLORS[5], this.GLOBALEAKS_COLORS[0], this.GLOBALEAKS_COLORS[1]]
          }]
        };
      default:
        return {
          labels: ['Value'],
          datasets: [{
            data: [metric.value],
            backgroundColor: [this.GLOBALEAKS_COLORS[0]]
          }]
        };
    }
  }

  private getChartOptions(chartType?: string): any {
    const baseOptions = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: true,
          position: 'bottom' as const,
          labels: {
            usePointStyle: true,
            padding: 20,
            generateLabels: function (chart: any) {
              const data = chart.data;
              if (data.labels.length && data.datasets.length) {
                return data.labels.map((label: string, i: number) => {
                  const value = data.datasets[0].data[i];
                  return {
                    text: `${label}: ${value}`,
                    fillStyle: data.datasets[0].backgroundColor[i],
                    hidden: false,
                    index: i
                  };
                });
              }
              return [];
            }
          }
        },
        tooltip: {
          callbacks: {
            label: function (context: any) {
              const label = context.label || '';
              const value = context.parsed || context.raw;
              return `${label}: ${value}`;
            }
          }
        }
      }
    };

    if (chartType === 'bar') {
      return {
        ...baseOptions,
        scales: {
          y: {
            beginAtZero: true,
            ticks: {
              callback: function (value: any) {
                return value;
              }
            }
          }
        }
      };
    }

    if (chartType === 'pie') {
      return {
        ...baseOptions,
        cutout: '50%'
      };
    }

    return baseOptions;
  }

  canAddMoreMetrics(): boolean {
    const currentCardIds = this.metricCards.map(card => card.id);
    const currentChartIds = this.chartMetrics.map(chart => chart.id);
    const allCurrentIds = [...currentCardIds, ...currentChartIds];
    const availableToAdd = this.availableMetrics.filter(metric => !allCurrentIds.includes(metric.id));
    const canAdd = availableToAdd.length > 0;
    return canAdd;
  }

  manageMetric(metricId: string): void {
    let currentItem = this.metricCards.find(card => card.id === metricId);
    let isChart = false;

    if (!currentItem) {
      currentItem = this.chartMetrics.find(chart => chart.id === metricId);
      isChart = true;
    }

    if (!currentItem) return;

    const allCurrentIds = [
      ...this.metricCards.map(card => card.id),
      ...this.chartMetrics.map(chart => chart.id)
    ];

    const modalRef = this.modalService.open(ManageMetricModalComponent, {
      size: 'lg',
      backdrop: 'static',
      keyboard: false
    });

    modalRef.componentInstance.availableMetrics = this.availableMetrics;
    modalRef.componentInstance.currentMetricIds = allCurrentIds;
    modalRef.componentInstance.currentMetricCard = currentItem;

    modalRef.result.then((result: { metric: any, chartType: string }) => {
      if (result && result.metric) {
        const newMetricItem: MetricCard = {
          id: result.metric.id,
          title: result.metric.title,
          value: result.metric.value,
          chartType: result.chartType
        };
        if (isChart) {
          this.chartMetrics = this.chartMetrics.filter(chart => chart.id !== metricId);
        } else {
          this.metricCards = this.metricCards.filter(card => card.id !== metricId);
        }
        const newIsChart = ['bar', 'pie'].includes(result.chartType);

        if (newIsChart) {
          this.chartMetrics.push(newMetricItem);
          this.updateChartConfigs();
        } else {
          this.metricCards.push(newMetricItem);
        }
        this.saveSelectedMetrics();
      }
    })
  }

  private saveSelectedMetrics(): void {
    const selectedCardIds = this.metricCards.map(card => card.id);
    const selectedChartIds = this.chartMetrics.map(card => ({ id: card.id, chartType: card.chartType }));
    localStorage.setItem('selected_metrics', JSON.stringify(selectedCardIds));
    localStorage.setItem('selected_chart_metrics', JSON.stringify(selectedChartIds));
    this.saveTemplateChanges()
  }

  exportReportAsPDF(): void {
    this.preparePrintContent();
    setTimeout(() => {
      window.print();
      this.removePrintContent();
    }, 100);
  }

  private preparePrintContent(): void {
    const contentDiv = document.getElementById('Content');
    if (!contentDiv) return;

    this.chartMetrics.forEach(chart => {
      const chartElement = document.querySelector(`canvas[data-chart-id="${chart.id}"]`)?.closest('.chart-card');
      if (chartElement) {
        const chartData = this.generateChartData(chart);
        const legendDiv = document.createElement('div');
        legendDiv.className = 'chart-legend print-legend';

        if (chartData.labels && chartData.datasets && chartData.datasets[0]) {
          legendDiv.innerHTML = chartData.labels.map((label: string, i: number) =>
            `<div class="legend-item">
              <span class="legend-color" style="background-color: ${chartData.datasets[0].backgroundColor?.[i] || '#3679BB'}"></span>
              <span>${label}: ${chartData.datasets[0].data?.[i] || 0}</span>
            </div>`
          ).join('');
        }

        chartElement.appendChild(legendDiv);
      }
    });
  }

  private removePrintContent(): void {
    document.querySelectorAll('.print-legend').forEach(el => el.remove());
  }

  saveTemplateChanges() {
    const currentTemplate = this.templateData;
    const updatedTemplate: ReportTemplate = {
      ...currentTemplate.data,
      config: {
        selectedMetrics: this.metricCards.map(card => ({
          id: card.id,
          title: card.title
        })),
        selectedCharts: this.chartMetrics.map(chart => ({
          id: chart.id,
          title: chart.title,
          chartType: chart.chartType
        }))
      },
    };
    this.currentTemplate = updatedTemplate;
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

  saveTemplate(template: statisticalTemplateResolverModel) {
    template.data = this.currentTemplate
    this.httpService.requestUpdateStatisticalTemplate(template.id, template).subscribe({});
  }
}
