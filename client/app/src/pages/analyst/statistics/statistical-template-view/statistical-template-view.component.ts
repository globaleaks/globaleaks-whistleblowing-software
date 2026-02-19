import {Component, Input, OnInit, inject} from "@angular/core";
import {CommonModule} from "@angular/common";
import {DatePipe, NgClass} from "@angular/common";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {ChartConfig, MetricCard, statisticalTemplateResolverModel} from "@app/models/resolvers/statistical-template-resolver-model";
import {StatisticsResolver} from "@app/shared/resolvers/statistics.resolver";
import {provideCharts, withDefaultRegisterables, BaseChartDirective} from "ng2-charts";
import {TranslateModule} from "@ngx-translate/core";
import {ReportTemplate} from "@app/models/analyst/report-template.model";

@Component({
  selector: 'src-statistical-template-view',
  templateUrl: './statistical-template-view.component.html',
  standalone: true,
  providers: [provideCharts(withDefaultRegisterables())],
  imports: [DatePipe, CommonModule, NgClass, TranslatorPipe, TranslateModule, BaseChartDirective]
})
export class StatisticalTemplateViewComponent implements OnInit {
  protected statisticsResolver = inject(StatisticsResolver);

  @Input() templateData!: statisticalTemplateResolverModel | null;
  @Input() templatesData: statisticalTemplateResolverModel[] = [];

  chartConfigs: ChartConfig[] = [];
  availableMetrics: MetricCard[] = [];
  metricCards: MetricCard[] = [];
  chartMetrics: MetricCard[] = [];

  private readonly GLOBALEAKS_COLORS = [
    '#3679BB', '#205282', '#9FC9F1', '#103253', '#4BC0C0', '#FFCE56', '#36A2EB', '#5A9FD4'
  ];

  ngOnInit(): void {
    this.initializeComponentWithTemplate(this.templateData);
  }

  private initializeComponentWithTemplate(template: any): void {
    this.initializeMetrics();
    this.loadTemplateConfiguration(template);
    this.initializeCharts();
  }

  private getFilteredStatistics() {
    return this.statisticsResolver.dataModel;
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
        return { labels: ['Anonymous', 'Identified'], datasets: [{ data: [dataModel.reports_anonymous || 0, (dataModel.reports_count || 0) - (dataModel.reports_anonymous || 0)], backgroundColor: [this.GLOBALEAKS_COLORS[2], this.GLOBALEAKS_COLORS[0]] }] };
      case 'reports_access_status':
        return { labels: ['Accessed', 'Not Accessed'], datasets: [{ data: [(dataModel.reports_count || 0) - (dataModel.reports_with_no_access || 0), dataModel.reports_with_no_access || 0], backgroundColor: [this.GLOBALEAKS_COLORS[4], this.GLOBALEAKS_COLORS[1]] }] };
      case 'reports_platform_distribution':
        return { labels: ['Mobile', 'Web', 'Tor'], datasets: [{ data: [dataModel.reports_mobile || 0, (dataModel.reports_count || 0) - (dataModel.reports_mobile || 0) - (dataModel.reports_tor || 0), dataModel.reports_tor || 0], backgroundColor: [this.GLOBALEAKS_COLORS[5], this.GLOBALEAKS_COLORS[0], this.GLOBALEAKS_COLORS[1]] }] };
      default:
        return { labels: ['Value'], datasets: [{ data: [metric.value], backgroundColor: [this.GLOBALEAKS_COLORS[0]] }] };
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

  private updateChartConfigs(): void {
    this.chartConfigs = [];
    this.chartMetrics.forEach((chartMetric) => {
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
}
