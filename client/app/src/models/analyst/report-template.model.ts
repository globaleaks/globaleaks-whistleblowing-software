export interface ReportTemplate {
  id: string;
  label: string;
  creation_date: string;
  data: {
    config: ReportTemplateConfig;
    permissions: ReportTemplatePermissions;
  }
}

export interface ReportTemplateConfig {
  selectedMetrics: string[];
  selectedCharts: string[];
}

export interface ReportTemplatePermissions {
  canEdit: boolean;
  canDelete: boolean;
  canShare?: boolean;
  canExport: boolean;
}