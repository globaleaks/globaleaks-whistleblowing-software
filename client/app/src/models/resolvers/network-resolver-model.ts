export class networkResolverModel {
  anonymize_outgoing_connections: boolean;
  hostname: string;
  https_admin: boolean;
  https_custodian: boolean;
  https_receiver: boolean;
  https_analyst: boolean;
  https_auditor: boolean;
  https_whistleblower: boolean;
  ip_filter_admin: string;
  ip_filter_admin_enable: boolean;
  ip_filter_custodian: string;
  ip_filter_custodian_enable: boolean;
  ip_filter_receiver: string;
  ip_filter_receiver_enable: boolean;
  ip_filter_analyst_enable: boolean;
  ip_filter_analyst: string;
  onionservice: string;
  reachable_via_web: boolean;
}