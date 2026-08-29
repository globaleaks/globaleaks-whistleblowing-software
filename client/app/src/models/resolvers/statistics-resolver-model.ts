export class statisticsResolverModel {
  reports_count: number;
  reports_with_no_access: number;
  reports_anonymous: number;
  reports_subscribed: number;
  reports_initially_anonymous: number;
  reports_mobile: number;
  reports_tor: number;
  avg_opening_time_hours: number;
  avg_first_reply_time_hours: number;
  avg_closure_time_hours: number;
  avg_exchanges_per_report: number;
  total_exchanges: number;
  reports_with_exchanges: number;
  question_template_dropdown_metrics?: Array<{
    id: string;
    template_id: string;
    title: string;
    total_answers: number;
    options: Array<{
      id: string;
      label: string;
      count: number;
      percentage: number;
    }>;
  }>;
}
