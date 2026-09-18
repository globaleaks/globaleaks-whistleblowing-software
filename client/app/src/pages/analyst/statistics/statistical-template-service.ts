import {inject, Injectable} from "@angular/core";
import {TranslateService} from "@ngx-translate/core";
import type {Chart, ChartOptions, TooltipItem} from "chart.js";
import {ChartConfig, MetricCard, StatisticalReportTemplate, statisticalTemplateResolverModel} from "@app/models/resolvers/statistical-template-resolver-model";
import {statisticsResolverModel} from "@app/models/resolvers/statistics-resolver-model";

// The metrics of the dropdown questions, as the statistics carry them with
// their values and as the catalog carries them without
interface DropdownOption {id: string; label: string; count?: number}
interface DropdownMetric {id: string; template_id: string; title: string; total_answers?: number; options: DropdownOption[]}
type MetricSource = Partial<Omit<statisticsResolverModel, "question_template_dropdown_metrics">> &
  {question_template_dropdown_metrics?: DropdownMetric[]};

// What a template names among the metrics: the identifier alone, or the
// identifier with the chart the metric is drawn as
type TemplateSelection = string | {id: string; chartType?: string};
interface TemplateConfig {
  selectedMetrics?: TemplateSelection[];
  selectedCharts?: TemplateSelection[];
}
type StatisticalTemplate = StatisticalReportTemplate | statisticalTemplateResolverModel;

@Injectable({
  providedIn: "root"
})
export class StatisticalTemplateService {
  private readonly translateService = inject(TranslateService);

  GLOBALEAKS_COLORS = [
    '#3679BB', '#205282', '#9FC9F1', '#103253', '#4BC0C0', '#FFCE56', '#36A2EB', '#5A9FD4'
  ];

  createMetricCatalog(dataModel: MetricSource): MetricCard[] {
    const toNumber = (value: unknown): number => Number(value) || 0;
    const toFixed1 = (value: number): string => value.toFixed(1);
    const toDurationLabel = (hoursValue: unknown): string => {
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
    });

    const distributionMetric = (id: string, title: string, labels: string[], data: number[]): MetricCard => ({
      id,
      title,
      value: data.reduce((sum, value) => sum + value, 0),
      metricType: 'standard',
      category: 'distribution',
      group: 'Default',
      compatibleTypes: ['pie', 'bar', 'percentage'],
      customData: { labels, data }
    });

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

    const customDropdownCatalog: MetricCard[] = dropdownTemplateMetrics.map((metric: DropdownMetric) => {
      const optionEntries = Array.isArray(metric.options) ? metric.options : [];
      const labels = optionEntries.map((option: DropdownOption) => option.label || option.id || '');
      const values = optionEntries.map((option: DropdownOption) => Number(option.count) || 0);
      const totalAnswers = Number(metric.total_answers) || values.reduce((sum: number, value: number) => sum + value, 0);

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

  loadTemplateConfiguration(template: StatisticalTemplate | null | undefined, availableMetrics: MetricCard[]) {
    const config: TemplateConfig = template?.data?.config || {};
    const metricCards: MetricCard[] = [];
    const chartMetrics: MetricCard[] = [];

    const selectedMetrics: TemplateSelection[] = config.selectedMetrics || [];
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

    const selectedCharts: TemplateSelection[] = config.selectedCharts || [];
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
      const values = card.customData.data.map((value: unknown) => Number(value) || 0);
      const total = values.reduce((sum: number, value: number) => sum + value, 0);
      const share = total > 0 ? ((values[0] ?? 0) / total) * 100 : 0;
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

  generateChartData(metric: MetricCard, dataModel: MetricSource | null | undefined, preview = false) {
    if (!dataModel) return { labels: [], datasets: [] };

    if (metric.customData && metric.customData.labels && metric.customData.data) {
      // While a template is composed the chart carries no value: it is drawn on
      // equal slices, so that the shape of what is being composed is visible
      const data = preview ? metric.customData.labels.map(() => 1) : metric.customData.data;

      return {
        labels: metric.customData.labels,
        datasets: [{
          data,
          backgroundColor: metric.customData.labels.map((_: string, index: number) => this.GLOBALEAKS_COLORS[index % this.GLOBALEAKS_COLORS.length])
        }]
      };
    }

    return { labels: [this.translateService.instant('Value')], datasets: [{ data: [preview ? 1 : metric.value], backgroundColor: [this.GLOBALEAKS_COLORS[0]] }] };
  }

  private getChartOptions(chartType?: string, preview = false): ChartOptions<'bar' | 'pie'> {
    const getTooltipValue = (context: TooltipItem<'bar' | 'pie'>): number | string => {
      if (typeof context.raw === 'number' || typeof context.raw === 'string') {
        return context.raw;
      }

      if (typeof context.parsed === 'number' || typeof context.parsed === 'string') {
        return context.parsed;
      }

      // A bar carries the value on one of its axes, a slice carries it alone
      const parsed: unknown = context.parsed;
      if (parsed && typeof parsed === 'object') {
        const point = parsed as {x?: unknown; y?: unknown};
        if (typeof point.y === 'number' || typeof point.y === 'string') {
          return point.y;
        }

        if (typeof point.x === 'number' || typeof point.x === 'string') {
          return point.x;
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
            generateLabels: function (chart: Chart) {
              const data = chart.data;
              const labels = data.labels ?? [];
              if (labels.length && data.datasets.length) {
                return labels.map((rawLabel, i) => {
                  const label = String(rawLabel);
                  const value = data.datasets[0]?.data[i];
                  return {
                    text: preview ? label : `${label}: ${value}`,
                    fillStyle: (data.datasets[0]?.backgroundColor as string[] | undefined)?.[i],
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
            label: function (context: TooltipItem<'bar' | 'pie'>) {
              const label = context.label || '';
              if (preview) {
                return label;
              }

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
              callback: function (value: string | number) {
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

  buildChartConfigs(chartMetrics: MetricCard[], dataModel: MetricSource, preview = false): ChartConfig[] {
    return chartMetrics.map(chartMetric => ({
      id: `chart-${chartMetric.id}`,
      title: chartMetric.title,
      type: this.getChartType(chartMetric.chartType),
      data: this.generateChartData(chartMetric, dataModel, preview),
      options: this.getChartOptions(chartMetric.chartType, preview)
    }));
  }
}
