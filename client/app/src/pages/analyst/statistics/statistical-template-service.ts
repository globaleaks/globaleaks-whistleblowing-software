import {Injectable} from "@angular/core";
import {ChartConfig, MetricCard} from "@app/models/resolvers/statistical-template-resolver-model";

@Injectable({
  providedIn: "root"
})
export class StatisticalTemplateService {

  GLOBALEAKS_COLORS = [
    '#3679BB', '#205282', '#9FC9F1', '#103253', '#4BC0C0', '#FFCE56', '#36A2EB', '#5A9FD4'
  ];

  getMetricCompatibility(metricId: string) {
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
      return { category: 'numeric', compatibleTypes: ['number', 'percentage'] } as const;
    } else if (comparativeMetrics.includes(metricId)) {
      return { category: 'comparative', compatibleTypes: ['number', 'percentage', 'pie'] } as const;
    } else if (distributionMetrics.includes(metricId)) {
      return { category: 'distribution', compatibleTypes: ['number', 'bar', 'pie'] } as const;
    }

    return { category: 'numeric', compatibleTypes: ['number', 'percentage'] } as const;
  }

  createMetricCatalog(dataModel: any): MetricCard[] {
    const toNumber = (value: any): number => Number(value) || 0;
    const toFixed1 = (value: number): string => value.toFixed(1);

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
    const reports_desktop = Math.max(0, reports_count - mobile_reports);
    const reports_direct = Math.max(0, reports_count - tor_reports);

    const disclosure_rate = reports_count > 0 ? toFixed1(((subscribed_reports + initially_anonymous_reports) / reports_count) * 100) : "0.0";
    const access_rate = reports_count > 0 ? toFixed1((reports_accessed / reports_count) * 100) : "0.0";
    const anonymity_rate = reports_count > 0 ? toFixed1((anonymous_reports / reports_count) * 100) : "0.0";
    const tor_usage_rate = reports_count > 0 ? toFixed1((tor_reports / reports_count) * 100) : "0.0";
    const mobile_usage_rate = reports_count > 0 ? toFixed1((mobile_reports / reports_count) * 100) : "0.0";
    const later_disclosure_rate = reports_count > 0 ? toFixed1((initially_anonymous_reports / reports_count) * 100) : "0.0";

    const createMetric = (id: string, title: string, value: number | string): MetricCard => {
      const compatibility = this.getMetricCompatibility(id);
      return {
        id,
        title,
        value,
        metricType: 'standard',
        category: compatibility.category,
        compatibleTypes: compatibility.compatibleTypes
      } as any;
    };

    const newCatalog: MetricCard[] = [
      createMetric('reports_received', 'Total Reports', reports_count),
      createMetric('reports_accessed', 'Accessed Reports', `${reports_accessed} (${access_rate}%)`),
      createMetric('reports_not_accessed', 'Unaccessed Reports', `${reports_with_no_access} (${toFixed1(100 - toNumber(access_rate))}%)`),
      createMetric('anonymous_reports', 'Anonymous Reports', `${anonymous_reports} (${anonymity_rate}%)`),
      createMetric('subscribed_reports', 'Subscribed Reports', `${subscribed_reports} (${reports_count > 0 ? toFixed1((subscribed_reports / reports_count) * 100) : "0.0"}%)`),
      createMetric('initially_anonymous_reports', 'Later Disclosed Identity', `${initially_anonymous_reports} (${later_disclosure_rate}%)`),
      createMetric('tor_reports', 'Tor Reports', `${tor_reports} (${tor_usage_rate}%)`),
      createMetric('direct_reports', 'Direct Connection', `${reports_direct} (${toFixed1(100 - toNumber(tor_usage_rate))}%)`),
      createMetric('mobile_reports', 'Mobile Reports', `${mobile_reports} (${mobile_usage_rate}%)`),
      createMetric('desktop_reports', 'Desktop Reports', `${reports_desktop} (${toFixed1(100 - toNumber(mobile_usage_rate))}%)`),
      createMetric('disclosure_rate', 'Identity Disclosure Rate', `${disclosure_rate}%`),
      createMetric('security_usage', 'High Security Reports', `${tor_reports + anonymous_reports}`),
      createMetric('avg_access_time', 'Average timing of opening of report', `${(dataModel.avg_opening_time_hours ?? dataModel.avg_access_time_hours ?? 0)}h`),
      createMetric('avg_response_time', 'Average timing of first reply', `${(dataModel.avg_first_reply_time_hours ?? dataModel.avg_response_time_hours ?? 0)}h`),
      createMetric('avg_disclosure_time', 'Average timing of closure of report', `${(dataModel.avg_closure_time_hours ?? dataModel.avg_identity_disclosure_time_hours ?? 0)}h`),
      createMetric('avg_exchanges', 'Average Exchanges per Report', toFixed1(toNumber(dataModel.avg_exchanges_per_report))),
      createMetric('total_exchanges', 'Total Exchanges', dataModel.total_exchanges || 0),
      createMetric('reports_with_exchanges', 'Reports with Exchanges', dataModel.reports_with_exchanges || 0),
      createMetric('reports_anonymous_vs_identified', 'Anonymous vs Identified Reports', `${reports_anonymous}/${reports_count - reports_anonymous}`),
      createMetric('reports_access_status', 'Access Status Distribution', `${reports_count - reports_with_no_access}/${reports_with_no_access}`),
      createMetric('reports_platform_distribution', 'Platform Distribution', `Mobile: ${reports_mobile}, Web: ${Math.max(0, reports_count - reports_mobile - reports_tor)}, Tor: ${reports_tor}`)
    ];

    const dropdownTemplateMetrics = Array.isArray(dataModel.question_template_dropdown_metrics)
      ? dataModel.question_template_dropdown_metrics
      : [];

    const customDropdownCatalog: MetricCard[] = dropdownTemplateMetrics.map((metric: any) => {
      const optionEntries = Array.isArray(metric.options) ? metric.options : [];
      const labels = optionEntries.map((option: any) => option.label || option.id || '');
      const values = optionEntries.map((option: any) => Number(option.count) || 0);
      const totalAnswers = Number(metric.total_answers) || values.reduce((sum:any, value:any) => sum + value, 0);

      return {
        id: metric.id || `question_template_dropdown_${metric.template_id}`,
        title: metric.title || metric.template_id || 'Dropdown Question',
        value: totalAnswers,
        metricType: 'question_template_dropdown',
        category: 'distribution',
        compatibleTypes: ['number', 'pie', 'bar'],
        customData: {
          labels,
          data: values
        }
      };
    });

    return [...newCatalog, ...customDropdownCatalog];
  }

  loadTemplateConfiguration(template: any, availableMetrics: MetricCard[]) {
    const metricCards: MetricCard[] = [];
    const chartMetrics: MetricCard[] = [];

    const selectedMetrics: any[] = (template?.data?.config && (template.data.config as any).selectedMetrics) ? (template.data.config as any).selectedMetrics : [];
    if (selectedMetrics && selectedMetrics.length > 0) {
      const templateMetrics = selectedMetrics
        .map(metricItem => {
          const metricId = typeof metricItem === 'string' ? metricItem : metricItem.id;
          return availableMetrics.find(m => m.id === metricId);
        })
        .filter((m): m is MetricCard => !!m);
      metricCards.push(...templateMetrics.map(metric => ({ ...metric, chartType: metric.chartType || 'number' })));
    }

    if (metricCards.length === 0) {
      if (availableMetrics.length >= 3) {
        metricCards.push(...availableMetrics.slice(0, 3).map(metric => ({ ...metric, chartType: 'number' })));
      }
    }

    const selectedCharts: any[] = (template?.data?.config && (template.data.config as any).selectedCharts) ? (template.data.config as any).selectedCharts : [];
    if (selectedCharts && selectedCharts.length > 0) {
      const templateCharts = selectedCharts
        .map(chartItem => {
          const chartId = typeof chartItem === 'string' ? chartItem : chartItem.id;
          const chartType = typeof chartItem === 'string' ? 'pie' : (chartItem.chartType || 'pie');
          const found = availableMetrics.find(m => m.id === chartId);
          return found ? { ...found, chartType } : null;
        })
        .filter((m): m is MetricCard & { chartType: string } => !!m);

      chartMetrics.push(...templateCharts);
    }

    return { metricCards, chartMetrics };
  }

  getChartType(chartType?: string): 'bar' | 'pie' | 'line' {
    switch (chartType) {
      case 'bar': return 'bar';
      case 'pie': return 'pie';
      case 'line': return 'line';
      default: return 'pie';
    }
  }

  generateChartData(metric: MetricCard, dataModel: any) {
    if (!dataModel) return { labels: [], datasets: [] };

    if (metric.customData && metric.customData.labels && metric.customData.data) {
      return {
        labels: metric.customData.labels,
        datasets: [{
          data: metric.customData.data,
          backgroundColor: metric.customData.data.map((_: number, index: number) => this.GLOBALEAKS_COLORS[index % this.GLOBALEAKS_COLORS.length])
        }]
      };
    }

    switch (metric.id) {
      case 'reports_anonymous_vs_identified':
        return {
          labels: ['Anonymous', 'Identified'],
          datasets: [{ data: [dataModel.reports_anonymous || 0, (dataModel.reports_count || 0) - (dataModel.reports_anonymous || 0)], backgroundColor: [this.GLOBALEAKS_COLORS[2], this.GLOBALEAKS_COLORS[0]] }]
        };
      case 'reports_access_status':
        return {
          labels: ['Accessed', 'Not Accessed'],
          datasets: [{ data: [(dataModel.reports_count || 0) - (dataModel.reports_with_no_access || 0), dataModel.reports_with_no_access || 0], backgroundColor: [this.GLOBALEAKS_COLORS[4], this.GLOBALEAKS_COLORS[1]] }]
        };
      case 'reports_platform_distribution':
        return {
          labels: ['Mobile', 'Web', 'Tor'],
          datasets: [{ data: [dataModel.reports_mobile || 0, (dataModel.reports_count || 0) - (dataModel.reports_mobile || 0) - (dataModel.reports_tor || 0), dataModel.reports_tor || 0], backgroundColor: [this.GLOBALEAKS_COLORS[5], this.GLOBALEAKS_COLORS[0], this.GLOBALEAKS_COLORS[1]] }]
        };
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

  buildChartConfigs(chartMetrics: MetricCard[], dataModel: any): ChartConfig[] {
    return chartMetrics.map(chartMetric => ({
      id: `chart-${chartMetric.id}`,
      title: chartMetric.title,
      type: this.getChartType((chartMetric as any).chartType),
      data: this.generateChartData(chartMetric, dataModel),
      options: this.getChartOptions((chartMetric as any).chartType)
    }));
  }
}
