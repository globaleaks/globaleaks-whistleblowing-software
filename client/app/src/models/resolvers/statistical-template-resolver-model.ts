export class StatisticalReportTemplate {
  id: string;
  tid: number;
  label: string;
  creation_date: string;
  /** Whether the site holds the template and may therefore write it */
  editable: boolean;
  /** Whether the statistics of the site are presented with the template */
  default: boolean;
  data: any;
}

export class statisticalTemplateResolverModel {
  id: string;
  tid: number;
  label: string;
  creation_date: string;
  editable: boolean;
  default: boolean;
  data: any;
}

export class MetricCard {
  id: string;
  title: string;
  value: number | string;
  chartType?: string;
  description?: string;
  metricType?: 'standard' | 'question_template_dropdown';
  category?: 'numeric' | 'comparative' | 'distribution';
  group?: string;
  compatibleTypes?: string[];
  customData?: {
    labels: string[];
    data: number[];
  };
}

export class ChartType {
  value: string;
  label: string;
  icon: string;
}

export class ChartConfig {
  id: string;
  title: string;
  type: 'bar' | 'pie';
  data: any;
  options: any;
  labels?: string[];
  datasets?: any[];
}

export class ChannelFilterOption {
  id: string | number;
  label: string;
}

export class DateFilter {
  fromDate: string;
  toDate: string;
}

export class StatisticsFilter {
  channel?: Array<string | number>;
  date_from?: number | string;
  date_to?: number | string;
}

export class MetricModalResult {
  metric: MetricCard;
  chartType: string;
}

export class FilterOption {
  id: string | number;
  label: string;
}

export class FilterOptionsResponse {
  channel?: FilterOption[];
}

export class NewTemplate {
  label: string;
  data: Record<string, unknown>;
}