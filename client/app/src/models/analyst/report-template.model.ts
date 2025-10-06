export interface ReportTemplate {
  id: string;
  name: string;
  createdBy: string;
  createdDate: string;
  lastModified: string;
  isPublic?: boolean;
  isDefault?: boolean;
  
  // Configuration
  config: ReportTemplateConfig;
  
  // Sharing and permissions
  sharedWith?: string[];
  permissions: ReportTemplatePermissions;
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