export interface ReportTemplate {
  id: string;
  label: string;
  creation_date: string;
  data: ReportTemplateData;
}

export interface ReportTemplateConfig {
  selectedMetrics: (string | ReportTemplateMetric)[];
  selectedCharts: (string | ReportTemplateChart)[];
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
  channel?: (string | number)[];
  date_from?: number | string;
  date_to?: number | string;
}

export interface ReportTemplateData {
  config: ReportTemplateConfig;
  permissions: ReportTemplatePermissions;
}
