export interface TenantBackupInventory {
  tenant_name: string;
  tenant_id: number;
  details?: {
    url: string;
    subdomain: string;
    site_status: string;
    submissions: string;
    scoring: string;
    language: string;
    retention_days: number;
    maximum_filesize: number;
    active_users: number;
    disabled_users: number;
    admin_name: string;
    admin_status: string;
  };
  tenants: number;
  total_users: number;
  administrators: number;
  recipients: number;
  custodians: number;
  analysts: number;
  auditors: number;
  transmitters: number;
  channels: number;
  questionnaires: number;
  reports: number;
  comments: number;
  total_files: number;
  uploaded_files: number;
  attachments: number;
  logs?: number;
  total_file_size: string;
}
