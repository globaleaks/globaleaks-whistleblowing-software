export class StatisticalReportTemplate {
  id: string;
  tid: number;
  label: string;
  creation_date: string;
  data: any;
}

export class statisticalTemplateResolverModel {
  id: string;
  tid: number;
  label: string;
  creation_date: string;
  data: any;
}

export class MetricCard {
  id: string;
  title: string;
  value: number | string;
  chartType?: string;
  description?: string;
  category?: 'numeric' | 'comparative' | 'distribution';
  compatibleTypes?: string[];
}

export class ChartType {
  value: string;
  label: string;
  icon: string;
}

export class ChartConfig {
  id: string;
  title: string;
  type: 'bar' | 'pie' | 'line';
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
  date_from?: number;
  date_to?: number;
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