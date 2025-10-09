import { Component, OnInit, inject } from '@angular/core';
import { firstValueFrom, of } from 'rxjs';
import { filter, take, timeout, catchError } from 'rxjs/operators';
import { Router, ActivatedRoute } from '@angular/router';
import { NgbModal, NgbTooltipModule, NgbDropdownModule } from '@ng-bootstrap/ng-bootstrap';
import { NgMultiSelectDropDownModule } from 'ng-multiselect-dropdown';
import { CommonModule } from '@angular/common';
import { TranslateModule } from '@ngx-translate/core';
import { FormsModule } from '@angular/forms';
import { StatisticsResolver } from '@app/shared/resolvers/statistics.resolver';
import { HttpService } from '@app/shared/services/http.service';
import { DateRangeSelectorComponent } from '@app/shared/components/date-selector/date-selector.component';
import { ReportTemplateService } from '@app/services/helper/report-template.service';
import { ReportTemplate } from '@app/models/analyst/report-template.model';
import {BaseChartDirective, provideCharts, withDefaultRegisterables} from 'ng2-charts';
import {AddMetricModalComponent} from '@app/shared/modals/add-metric-modal/add-metric-modal.component';
import {ManageMetricModalComponent} from '@app/shared/modals/manage-metric-modal/manage-metric-modal.component';

interface MetricCard {
  id: string;
  title: string;
  value: number | string;
  chartType?: string; // 'number', 'percentage', 'pie', 'bar'
  category?: 'numeric' | 'comparative' | 'distribution';
  compatibleTypes?: string[];
}

interface ChartConfig {
  id: string;
  title: string;
  type: 'bar' | 'pie' | 'line';
  data: any;
  options: any;
  labels?: string[];
  datasets?: any[];
}

@Component({
    selector: 'src-statistics',
    templateUrl: './statistics.component.html',
    styleUrl: './statistics.component.css',
    standalone: true,
  providers: [provideCharts(withDefaultRegisterables())],
    imports: [
    CommonModule,
    TranslateModule,
    FormsModule,
    NgbTooltipModule,
    NgbDropdownModule,
    NgMultiSelectDropDownModule,
    DateRangeSelectorComponent,
    BaseChartDirective
  ]
})
export class StatisticsComponent implements OnInit {
  private modalService = inject(NgbModal);
  private statisticsResolver = inject(StatisticsResolver);
  private httpService = inject(HttpService);
  private router = inject(Router);
  private activatedRoute = inject(ActivatedRoute);
  private reportTemplateService = inject(ReportTemplateService);

  // Chart configurations for different views
  chartConfigs: ChartConfig[] = [];

  // Data properties
  availableMetrics: MetricCard[] = [];
  metricCards: MetricCard[] = [];
  chartMetrics: MetricCard[] = [];

  // GlobalLeaks Brand Colors
  private readonly GLOBALEAKS_COLORS = [
    '#3679BB', // Primary blue
    '#205282', // Dark blue
    '#9FC9F1', // Light blue
    '#103253', // Very dark blue
    '#4BC0C0', // Teal
    '#FFCE56', // Yellow
    '#36A2EB', // Sky blue
    '#5A9FD4'  // Medium blue
  ];

  // UI state for filtering
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
  dateModel: any = null; // For date picker component

  // Filter status tracking
  currentFilteredData: any = null;

  // For the date picker component
  currentData: any = null;
  calculatedValue: any = null;

  // Template viewing mode
  templateViewMode: 'view' | 'edit' | null = null;
  currentTemplateId: string | null = null;
  currentTemplate: any = null;
  isAutoSaving: boolean = false;
  templateNameEdit: string = '';
  isEditingInline: boolean = false;

  // Dropdown settings for NgMultiSelect
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

  // Compact dropdown settings for filters
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
    // Check URL parameters to understand the intended mode
    const urlTemplate = this.activatedRoute.snapshot.queryParams['template'];
    const urlMode = this.activatedRoute.snapshot.queryParams['mode'];

    // Store current template ID for navigation and saving
    this.currentTemplateId = urlTemplate || null;

    // Set template viewing mode based on URL
    if (urlMode === 'view' || urlMode === 'edit') {
      this.templateViewMode = urlMode;

    } else {
      this.templateViewMode = 'view';

    }
    this.checkTemplateConfiguration().catch(() => {
      // Error handled by redirection
    });
  }

  private async checkTemplateConfiguration(): Promise<void> {
    // check template configuration
    try {
      // Check if we have a specific template to load from query params
      const urlTemplate = this.activatedRoute.snapshot.queryParams['template'];
      const urlMode = this.activatedRoute.snapshot.queryParams['mode'];

      // If no specific template requested, redirect to templates page immediately
      if (!urlTemplate) {
        this.router.navigate(['/analyst/templates']);
        return;
      }

      // Store current template ID
      this.currentTemplateId = urlTemplate;

      // Set template viewing mode
      if (urlMode === 'view' || urlMode === 'edit') {
        this.templateViewMode = urlMode;
      } else {
        this.templateViewMode = 'view';
      }

      // Check if service is available
      if (!this.reportTemplateService) {
        this.router.navigate(['/analyst/templates']);
        return;
      }

      // Get available templates with better error handling
      try {
        // Get the first emission quickly (may be empty), then handle fallbacks
        let templates: any[] = await firstValueFrom(
          this.reportTemplateService.getTemplates().pipe(
            take(1),
            timeout(5000),
            catchError(() => of([]))
          )
        );

        // Load specific template from URL parameter
        let template = (templates || []).find(t => t.id === urlTemplate);
        if (!template) {
          // Fetch directly from backend as a fallback if list is not yet populated
          try {
            template = await firstValueFrom(
              this.httpService.getTemplate(urlTemplate).pipe(
                timeout(3000),
                catchError((error) => {
                  throw error;
                })
              )
            );

            // If we loaded it directly, promote it to current list for subsequent use
            if (template) {
              this.currentTemplate = template;
              await this.initializeComponentWithTemplate(template);
              return;
            }
          } catch (fetchError) {
            // Template not found - redirect to templates page
            this.router.navigate(['/analyst/templates']);
            return;
          }
        }

        if (template) {
          this.currentTemplate = template; // Store current template for display
          await this.initializeComponentWithTemplate(template);
          return;
        } else {
          // Template not found - redirect to templates page
          this.router.navigate(['/analyst/templates']);
          return;
        }

      } catch (serviceError) {
        // On error, redirect to templates page
        this.router.navigate(['/analyst/templates']);
        return;
      }
    } catch (error) {
      // On any critical error, redirect to templates page
      this.router.navigate(['/analyst/templates']);
    }
  }

  private loadTemplateConfiguration(template: ReportTemplate): void {

    // Reset current selections
    this.metricCards = [];
    this.chartMetrics = [];

    // Apply template metrics configuration
    const selectedMetrics: any[] = (template.config && (template.config as any).selectedMetrics) ? (template.config as any).selectedMetrics : [];

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
    } else {
      // If no metrics are configured in template, set some default metrics
    }

    // Always apply fallback if no metrics were mapped
    if (this.metricCards.length === 0) {

      if (this.availableMetrics.length >= 3) {
        this.metricCards = this.availableMetrics.slice(0, 3).map(metric => ({
          ...metric,
          chartType: 'number'
        }));

      }
    }

    // Apply template charts configuration
    const selectedCharts: any[] = (template.config && (template.config as any).selectedCharts) ? (template.config as any).selectedCharts : [];

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

    // Apply template filters if any
    if (template.config && (template.config as any).defaultFilters) {
      // Hook for future filter application
    }
  }

  private async initializeComponentWithTemplate(template: ReportTemplate): Promise<void> {
    this.initializeFilters();

    try {
      await this.statisticsResolver.resolve({}).toPromise();
    } catch (error) {
      // Error handled silently
    }

    // Ensure available metrics are populated
    this.initializeMetrics();

    // Re-apply the template mapping now that metrics are available
    this.loadTemplateConfiguration(template);

    // Initialize charts from the mapped selection
    this.initializeCharts();

    // Persist selection for subsequent loads
    this.saveSelectedMetrics();
  }

  private getFilteredStatistics() {
    return this.currentFilteredData || this.statisticsResolver.dataModel;
  }

  private initializeCharts(): void {
    // Initialize chart configurations based on selected chart metrics
    this.updateChartConfigs();
  }

  private getMetricCompatibility(metricId: string): { category: 'numeric' | 'comparative' | 'distribution', compatibleTypes: string[] } {
    // Numeric-only metrics (single values, averages, totals)
    const numericOnlyMetrics = [
      'reports_received', 'avg_access_time', 'avg_response_time', 'avg_disclosure_time',
      'avg_exchanges', 'total_exchanges', 'reports_with_exchanges', 'security_usage'
    ];

    // Comparative metrics (can be displayed as numbers or simple charts)
    const comparativeMetrics = [
      'reports_accessed', 'reports_not_accessed', 'anonymous_reports', 'subscribed_reports',
      'initially_anonymous_reports', 'tor_reports', 'direct_reports', 'mobile_reports',
      'desktop_reports', 'disclosure_rate'
    ];

    // Distribution metrics (designed for charts, can also be numbers)
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
      // Default for unknown metrics
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

    // Get basic statistics from backend
    const reports_count = dataModel.reports_count || 0;
    const reports_with_no_access = dataModel.reports_with_no_access || 0;
    const reports_anonymous = dataModel.reports_anonymous || 0;
    const reports_subscribed = dataModel.reports_subscribed || 0;
    const reports_initially_anonymous = dataModel.reports_initially_anonymous || 0;
    const reports_mobile = dataModel.reports_mobile || 0;
    const reports_tor = dataModel.reports_tor || 0;

    // Calculate derived statistics
    const reports_accessed = reports_count - reports_with_no_access;
    const mobile_reports = reports_mobile;
    const tor_reports = reports_tor;
    const subscribed_reports = reports_subscribed;
    const initially_anonymous_reports = reports_initially_anonymous;
    const anonymous_reports = reports_anonymous;
    const reports_desktop = reports_count - mobile_reports;
    const reports_direct = reports_count - tor_reports;

    // Calculate percentage metrics
    const disclosure_rate = reports_count > 0 ? ((subscribed_reports + initially_anonymous_reports) / reports_count * 100).toFixed(1) : 0;
    const access_rate = reports_count > 0 ? (reports_accessed / reports_count * 100).toFixed(1) : 0;
    const anonymity_rate = reports_count > 0 ? (anonymous_reports / reports_count * 100).toFixed(1) : 0;
    const tor_usage_rate = reports_count > 0 ? (tor_reports / reports_count * 100).toFixed(1) : 0;
    const mobile_usage_rate = reports_count > 0 ? (mobile_reports / reports_count * 100).toFixed(1) : 0;
    const later_disclosure_rate = reports_count > 0 ? (initially_anonymous_reports / reports_count * 100).toFixed(1) : 0;

    // Update availableMetrics with simplified backend data
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

    // Populate the catalog of metrics only once if empty to keep references stable
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

      // Time-based metrics (if available from enhanced backend)
      createMetric('avg_access_time', 'Average Access Time', (dataModel as any).avg_access_time_hours ? `${(dataModel as any).avg_access_time_hours}h` : 'N/A'),
      createMetric('avg_response_time', 'Average Response Time', (dataModel as any).avg_response_time_hours ? `${(dataModel as any).avg_response_time_hours}h` : 'N/A'),
      createMetric('avg_disclosure_time', 'Average Identity Disclosure Time', (dataModel as any).avg_identity_disclosure_time_hours ? `${(dataModel as any).avg_identity_disclosure_time_hours}h` : 'N/A'),
      createMetric('avg_exchanges', 'Average Exchanges per Report', (dataModel as any).avg_exchanges_per_report ? (dataModel as any).avg_exchanges_per_report.toFixed(1) : 'N/A'),
      createMetric('total_exchanges', 'Total Exchanges', (dataModel as any).total_exchanges || 0),
      createMetric('reports_with_exchanges', 'Reports with Exchanges', (dataModel as any).reports_with_exchanges || 0),
      createMetric('reports_anonymous_vs_identified', 'Anonymous vs Identified Reports', `${reports_anonymous}/${reports_count - reports_anonymous}`),
      createMetric('reports_access_status', 'Access Status Distribution', `${reports_count - reports_with_no_access}/${reports_with_no_access}`),
      createMetric('reports_platform_distribution', 'Platform Distribution', `Mobile: ${reports_mobile}, Web: ${reports_count - reports_mobile - reports_tor}, Tor: ${reports_tor}`)
    ];

    if (this.availableMetrics.length === 0) {
      this.availableMetrics = newCatalog;
    } else {
      // Update values but keep the array reference
      this.availableMetrics = this.availableMetrics.map(existing => newCatalog.find(n => n.id === existing.id) || existing);
    }

    // Update existing metric cards with fresh data
    this.updateMetricCardsData();
  }

  private updateMetricCardsData(): void {
    // Refresh the displayed metric cards with new data from availableMetrics
    this.metricCards = this.metricCards.map(displayedCard => {
      const updatedMetric = this.availableMetrics.find(metric => metric.id === displayedCard.id);
      return updatedMetric || displayedCard;
    });
  }

  private async initializeFilters(): Promise<void> {
    try {
      // Load all filter options from backend
      const filterOptions = await this.httpService.requestFilterOptions().toPromise();

      // Set the dropdown data from backend response only
      this.statusDropdownData = filterOptions.status || [];
      this.tenantDropdownData = filterOptions.tenant || [];
      this.channelDropdownData = filterOptions.channel || [];

    } catch (error) {
      // Initialize with empty arrays if backend fails
      this.statusDropdownData = [];
      this.tagDropdownData = [];
      this.tenantDropdownData = [];
      this.channelDropdownData = [];
    }
  }

  // Filter toggle methods
  toggleStatusFilter(): void {
    this.statusDropdownVisible = !this.statusDropdownVisible;
    this.tagDropdownVisible = false; // Close other dropdowns
    this.tenantDropdownVisible = false;
    this.channelDropdownVisible = false;
    this.datePicker = false;
  }

  toggleTagFilter(): void {
    this.tagDropdownVisible = !this.tagDropdownVisible;
    this.statusDropdownVisible = false; // Close other dropdowns
    this.tenantDropdownVisible = false;
    this.channelDropdownVisible = false;
    this.datePicker = false;
  }

  toggleTenantFilter(): void {
    this.tenantDropdownVisible = !this.tenantDropdownVisible;
    this.statusDropdownVisible = false; // Close other dropdowns
    this.tagDropdownVisible = false;
    this.channelDropdownVisible = false;
    this.datePicker = false;
  }

  toggleChannelFilter(): void {
    this.channelDropdownVisible = !this.channelDropdownVisible;
    this.statusDropdownVisible = false; // Close other dropdowns
    this.tagDropdownVisible = false;
    this.tenantDropdownVisible = false;
    this.datePicker = false;
  }

  // Filter change handlers
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

    // Refresh data with no filters
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

    // Close dropdowns if clicking outside
    if (!target.closest('.filter-dropdown-container')) {
    this.statusDropdownVisible = false;
    this.tagDropdownVisible = false;
    this.tenantDropdownVisible = false;
    this.channelDropdownVisible = false;
    }

    // Close date picker if clicking outside
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

  private async refreshData(): Promise<void> {
    try {
      await this.statisticsResolver.resolve({}).toPromise();
    } catch (error) {
      // Error handled silently
    }
    this.initializeMetrics();
    this.initializeCharts();
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

  private async applyFilters() {
    try {
      // Prepare filter object for backend API
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

      // Call backend API with filters to get updated statistics
      const filteredData = await firstValueFrom(this.httpService.requestStatisticsResource(filters));
      this.currentFilteredData = filteredData;

      // Update the resolver's dataModel so metrics use filtered data
      this.statisticsResolver.dataModel = filteredData;

      // Update predefined metrics with new data
      this.initializeMetrics();

      // Update all charts with new data
      this.initializeCharts();
    } catch (error) {
      // Fallback to original data
      this.currentFilteredData = null;
    }
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

    modalRef.result.then((result: {metric: any, chartType: string, displayType: 'card' | 'chart'}) => {
      if (result && result.metric) {
        const newMetricCard: MetricCard = {
          id: result.metric.id,
          title: result.metric.title,
          value: result.metric.value,
          chartType: result.chartType,
          category: result.metric.category,
          compatibleTypes: result.metric.compatibleTypes
        };

        // Determine if it should be a chart or card based on chartType
        const isChart = ['bar', 'pie'].includes(result.chartType);

        if (isChart) {
          // Add as chart metric
          this.chartMetrics.push(newMetricCard);
        } else {
          // Add as card metric (number/percentage)
          this.metricCards.push(newMetricCard);
        }

        this.updateChartConfigs();
        this.saveSelectedMetrics();
      }
    }).catch(() => {
      // Modal dismissed
    });
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
    // Extract metric ID from chart ID (removes "chart-" prefix)
    return chartId.replace('chart-', '');
  }

  private updateChartConfigs(): void {
    // Update the chart configurations based on the selected chart metrics
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
    switch(chartType) {
      case 'bar': return 'bar';
      case 'pie': return 'pie';
      case 'line': return 'line';
      default: return 'pie';
    }
  }

  private generateChartData(metric: MetricCard): any {
    // Generate appropriate chart data based on the metric
    const dataModel = this.getFilteredStatistics();
    if (!dataModel) return { labels: [], datasets: [] };

    switch(metric.id) {
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
            generateLabels: function(chart: any) {
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
            label: function(context: any) {
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
              callback: function(value: any) {
                return value;
              }
            }
          }
        }
      };
    }

    // Add cutout for pie charts to maintain doughnut shape
    if (chartType === 'pie') {
      return {
        ...baseOptions,
        cutout: '50%'
      };
    }

    return baseOptions;
  }

  canAddMoreMetrics(): boolean {
    // Check if there are any metrics that haven't been added yet
    const currentCardIds = this.metricCards.map(card => card.id);
    const currentChartIds = this.chartMetrics.map(chart => chart.id);
    const allCurrentIds = [...currentCardIds, ...currentChartIds];
    const availableToAdd = this.availableMetrics.filter(metric => !allCurrentIds.includes(metric.id));
    const canAdd = availableToAdd.length > 0;
    return canAdd;
  }

  manageMetric(metricId: string): void {
    // Find the metric in either cards or charts
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

    modalRef.result.then((result: {metric: any, chartType: string}) => {
      if (result && result.metric) {
        const newMetricItem: MetricCard = {
          id: result.metric.id,
          title: result.metric.title,
          value: result.metric.value,
          chartType: result.chartType
        };

        // Remove from current location
        if (isChart) {
          this.chartMetrics = this.chartMetrics.filter(chart => chart.id !== metricId);
        } else {
          this.metricCards = this.metricCards.filter(card => card.id !== metricId);
        }

        // Add to appropriate location based on new chart type
        const newIsChart = ['bar', 'pie'].includes(result.chartType);

        if (newIsChart) {
          this.chartMetrics.push(newMetricItem);
          this.updateChartConfigs();
        } else {
          this.metricCards.push(newMetricItem);
        }

        this.saveSelectedMetrics();
      }
    }).catch(() => {
      // Modal dismissed/cancelled - no action needed
    });
  }

  private getCurrentFilters(): any {
    const filters: any = {};

    if (this.statusDropdownModel && this.statusDropdownModel.length > 0) {
      filters.status = this.statusDropdownModel.map(item => item.label || item.id);
    }

    if (this.dateFilter) {
      filters.date_from = this.dateFilter.fromDate;
      filters.date_to = this.dateFilter.toDate;
    }

    return filters;
  }

  private saveSelectedMetrics(): void {
    const selectedCardIds = this.metricCards.map(card => card.id);
    const selectedChartIds = this.chartMetrics.map(card => ({ id: card.id, chartType: card.chartType }));

    // Save to localStorage for standalone mode (fallback)
    localStorage.setItem('selected_metrics', JSON.stringify(selectedCardIds));
    localStorage.setItem('selected_chart_metrics', JSON.stringify(selectedChartIds));

    // If in template mode, also save to the template
    if (this.currentTemplateId && this.templateViewMode === 'edit') {
      this.isAutoSaving = true;
      this.saveTemplateChanges(false).then(() => {
        this.isAutoSaving = false;
      }).catch(() => {
        this.isAutoSaving = false;
      });
    }
  }

  private loadSelectedMetrics(): void {
    // Load card metrics
    const savedCards = localStorage.getItem('selected_metrics');
    if (savedCards) {
      try {
        const selectedIds = JSON.parse(savedCards);
        this.metricCards = selectedIds.map((id: string) =>
          this.availableMetrics.find(m => m.id === id)
        ).filter((card: MetricCard) => card !== undefined);
      } catch (error) {
        // Error handled silently
      }
    }

    // Load chart metrics
    const savedCharts = localStorage.getItem('selected_chart_metrics');
    if (savedCharts) {
      try {
        const selectedCharts = JSON.parse(savedCharts);
        this.chartMetrics = selectedCharts.map((chartInfo: any) => {
          const metric = this.availableMetrics.find(m => m.id === chartInfo.id);
          if (metric) {
            return { ...metric, chartType: chartInfo.chartType };
          }
          return undefined;
        }).filter((card: MetricCard) => card !== undefined);
      } catch (error) {
        // Error handled silently
      }
    }
  }

  exportReportAsPDF(): void {
    // Add print-ready content for the PDF
    this.preparePrintContent();

    // Trigger browser's print dialog
    setTimeout(() => {
      window.print();
      // Clean up after printing
      this.removePrintContent();
    }, 100);
  }

  private preparePrintContent(): void {
    const contentDiv = document.getElementById('Content');
    if (!contentDiv) return;

    // Add chart legends for print
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
    // Remove any generated legends
    document.querySelectorAll('.print-legend').forEach(el => el.remove());
  }

  // Template navigation and saving methods
  navigateBackToTemplates(): void {
    this.router.navigate(['/analyst/statistics']);
  }

  toggleEditMode(): void {
    this.isEditingInline = !this.isEditingInline;
    this.templateViewMode = this.isEditingInline ? 'edit' : 'view';
    if (this.templateViewMode === 'edit' && this.currentTemplate) {
      this.templateNameEdit = this.currentTemplate.name || '';
    }
  }

  async saveTemplateChanges(manual: boolean = false): Promise<void> {
    if (!this.currentTemplateId) {
      return;
    }

    try {
      // Get current template using direct subscription approach
      let templates: any[] = [];
      this.reportTemplateService.getTemplates().subscribe({
        next: (value) => {
          templates = value || [];
        },
        error: (error) => {
          throw error;
        }
      }).unsubscribe();

      const currentTemplate = templates.find(t => t.id === this.currentTemplateId);

      if (!currentTemplate) {
        return;
      }

      // Create updated template config with current metric and chart selections
      const updatedTemplate: ReportTemplate = {
        ...currentTemplate,
        lastModified: new Date().toISOString(),
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
        name: this.templateNameEdit && this.templateViewMode === 'edit' ? this.templateNameEdit : currentTemplate.name
      };

      // Save the updated template using direct subscription approach
      await firstValueFrom(this.reportTemplateService.saveTemplate(updatedTemplate));

      // Update the current template with the saved data to reflect changes in the UI
      this.currentTemplate = updatedTemplate;

      // If this was a manual save (Save button clicked), revert to view mode
      if (manual) {
        this.templateViewMode = 'view';
        this.isEditingInline = false;
      }
    } catch (error) {
      // Error handled silently
    }
  }

}
