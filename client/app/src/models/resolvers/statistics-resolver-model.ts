export class statisticsResolverModel {
  // Basic metrics
  reports_count: number;
  reports_with_no_access: number;
  reports_anonymous: number;
  reports_subscribed: number;
  reports_initially_anonymous: number;
  reports_mobile: number;
  reports_tor: number;
  
  // Time-based metrics (from enhanced backend)
  avg_access_time_hours?: number;
  avg_response_time_hours?: number;
  avg_identity_disclosure_time_hours?: number;
  avg_exchanges_per_report?: number;
  total_exchanges?: number;
  reports_with_exchanges?: number;
  }