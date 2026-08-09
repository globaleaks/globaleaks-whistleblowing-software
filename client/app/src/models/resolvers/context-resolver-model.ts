export class contextResolverModel {
  id: string;
  slug: string;
  hidden: boolean;
  is_forward_channel: boolean;
  tip_timetolive: number;
  tip_reminder: number;
  select_all_receivers: boolean;
  maximum_selectable_receivers: number;
  allow_recipients_selection: boolean;
  score_threshold_medium: number;
  score_threshold_high: number;
  order: number;
  show_receivers_in_alphabetical_order: boolean;
  show_steps_navigation_interface: boolean;
  questionnaire_id: string;
  additional_questionnaire_id: string;
  receivers: string[];
  picture: boolean;
  name: string;
  description: string;
}
