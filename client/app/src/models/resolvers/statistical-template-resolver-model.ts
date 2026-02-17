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
  category?: 'numeric' | 'comparative' | 'distribution';
  compatibleTypes?: string[];
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