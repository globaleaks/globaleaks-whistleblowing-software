export interface ReportTemplate {
  id: string;
  label: string;
  creation_date: string;
  data: ReportTemplateData;
}

export interface ReportTemplateConfig {
  selectedMetrics: Array<string | ReportTemplateMetric>;
  selectedCharts: Array<string | ReportTemplateChart>;
  filters?: ReportTemplateFilters;
}

export interface ReportTemplatePermissions {
  canEdit: boolean;
  canDelete: boolean;
  canShare?: boolean;
  canExport: boolean;
}

export interface ReportTemplateMetric {
  id: string;
  title?: string;
}

export interface ReportTemplateChart extends ReportTemplateMetric {
  chartType?: string;
}

export interface ReportTemplateFilters {
  channel?: Array<string | number>;
  date_from?: number;
  date_to?: number;
}

export interface ReportTemplateData {
  config: ReportTemplateConfig;
  permissions: ReportTemplatePermissions;
}
