import {inject, Injectable} from "@angular/core";
import {TranslateService} from "@ngx-translate/core";
import {ChartConfig, MetricCard} from "@app/models/resolvers/statistical-template-resolver-model";

@Injectable({
  providedIn: "root"
})
export class StatisticalTemplateService {
  private readonly translateService = inject(TranslateService);

  GLOBALEAKS_COLORS = [
    '#3679BB', '#205282', '#9FC9F1', '#103253', '#4BC0C0', '#FFCE56', '#36A2EB', '#5A9FD4'
  ];

  createMetricCatalog(dataModel: any): MetricCard[] {
    const toNumber = (value: any): number => Number(value) || 0;
    const toFixed1 = (value: number): string => value.toFixed(1);
    const toDurationLabel = (hoursValue: any): string => {
      const hours = toNumber(hoursValue);
      if (!Number.isFinite(hours) || hours <= 0) {
        return "0.0 days";
      }

      if (hours < 1) {
        const minutes = hours * 60;
        return `${toFixed1(minutes)} minutes`;
      }

      if (hours < 24) {
        return `${toFixed1(hours)} hours`;
      }

      const days = hours / 24;
      return `${toFixed1(days)} days`;
    };

    const reports_count = dataModel.reports_count || 0;
    const reports_with_no_access = dataModel.reports_with_no_access || 0;
    const reports_anonymous = dataModel.reports_anonymous || 0;
    const reports_subscribed = dataModel.reports_subscribed || 0;
    const reports_initially_anonymous = dataModel.reports_initially_anonymous || 0;
    const reports_mobile = dataModel.reports_mobile || 0;
    const reports_tor = dataModel.reports_tor || 0;

    const reports_accessed = Math.max(0, reports_count - reports_with_no_access);
    const reports_desktop = Math.max(0, reports_count - reports_mobile);
    const reports_direct = Math.max(0, reports_count - reports_tor);

    const t = (key: string): string => this.translateService.instant(key);

    const scalarMetric = (id: string, title: string, value: number | string): MetricCard => ({
      id,
      title,
      value,
      metricType: 'standard',
      category: 'numeric',
      group: 'Default',
      compatibleTypes: ['number']
    } as any);

    const distributionMetric = (id: string, title: string, labels: string[], data: number[]): MetricCard => ({
      id,
      title,
      value: data.reduce((sum, value) => sum + value, 0),
      metricType: 'standard',
      category: 'distribution',
      group: 'Default',
      compatibleTypes: ['pie', 'bar', 'percentage'],
      customData: { labels, data }
    } as any);

    const newCatalog: MetricCard[] = [
      scalarMetric('reports_received', 'Reports', reports_count),
      scalarMetric('avg_opening_time', 'Average time to opening', toDurationLabel(dataModel.avg_opening_time_hours ?? 0)),
      scalarMetric('avg_reply_time', 'Average time to first reply', toDurationLabel(dataModel.avg_first_reply_time_hours ?? 0)),
      scalarMetric('avg_closure_time', 'Average time to closure', toDurationLabel(dataModel.avg_closure_time_hours ?? 0)),
      scalarMetric('avg_exchanges', 'Average messages per report', toFixed1(toNumber(dataModel.avg_exchanges_per_report))),
      distributionMetric('returning_whistleblowers', 'Returning whistleblowers', [t('Yes'), t('No')], [reports_accessed, reports_with_no_access]),
      distributionMetric('anonymity', 'Anonymity', [t('Anonymous'), t('Subscribed'), t('Subscribed later')], [reports_anonymous, reports_subscribed, reports_initially_anonymous]),
      distributionMetric('tor', 'Tor', [t('Yes'), t('No')], [reports_tor, reports_direct]),
      distributionMetric('mobile', 'Mobile', [t('Yes'), t('No')], [reports_mobile, reports_desktop])
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
        group: 'Custom',
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
          const chartType = typeof metricItem === 'string' ? 'number' : (metricItem.chartType || 'number');
          const found = availableMetrics.find(m => m.id === metricId);
          return found ? this.presentCard({ ...found, chartType }) : null;
        })
        .filter((m): m is MetricCard => !!m);
      metricCards.push(...templateMetrics);
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

  presentCard(card: MetricCard): MetricCard {
    if (card.chartType === 'percentage' && card.customData?.data?.length) {
      const values = card.customData.data.map((value: any) => Number(value) || 0);
      const total = values.reduce((sum: number, value: number) => sum + value, 0);
      const share = total > 0 ? (values[0] / total) * 100 : 0;
      return { ...card, value: `${share.toFixed(1)}% ${card.customData.labels[0] || ''}`.trim() };
    }
    return card;
  }

  getChartType(chartType?: string): 'bar' | 'pie' {
    switch (chartType) {
      case 'bar': return 'bar';
      case 'pie': return 'pie';
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

    return { labels: [this.translateService.instant('Value')], datasets: [{ data: [metric.value], backgroundColor: [this.GLOBALEAKS_COLORS[0]] }] };
  }

  private getChartOptions(chartType?: string): any {
    const getTooltipValue = (context: any): number | string => {
      if (typeof context.raw === 'number' || typeof context.raw === 'string') {
        return context.raw;
      }

      if (typeof context.parsed === 'number' || typeof context.parsed === 'string') {
        return context.parsed;
      }

      if (context.parsed && typeof context.parsed === 'object') {
        if (typeof context.parsed.y === 'number' || typeof context.parsed.y === 'string') {
          return context.parsed.y;
        }

        if (typeof context.parsed.x === 'number' || typeof context.parsed.x === 'string') {
          return context.parsed.x;
        }
      }

      return '';
    };

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
              const value = getTooltipValue(context);
              return label ? `${label}: ${value}` : `${value}`;
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
