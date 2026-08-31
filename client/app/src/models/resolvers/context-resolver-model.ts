export class contextResolverModel {
  id: string;
  slug: string;
  hidden: boolean;
  exchange: boolean;
  exchange_types: string[];
  // The channel is offered to the users of the site that file a report on it
  // themselves, in place of a reporting person
  internally_available: boolean;
  provide_access_code: boolean;
  exchange_in_use: boolean;
  profiles: string[];
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
  // The additional questionnaires the channel can ask of its reports; the one
  // named by additional_questionnaire_id is the one it asks automatically
  additional_questionnaires: string[];
  receivers: string[];
  picture: boolean;
  name: string;
  description: string;
}
