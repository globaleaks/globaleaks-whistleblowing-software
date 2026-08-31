export class NewContext {
  id = "";
  slug = "";
  hidden = true;
  name = "";
  description = "";
  order = 0;
  tip_timetolive = 90;
  allow_recipients_selection = false;
  show_receivers_in_alphabetical_order = true;
  // A channel is offered to the reporting people alone until the site declares
  // it available to the users that file a report on it themselves
  internally_available = false;
  provide_access_code = false;
  show_steps_navigation_interface = true;
  select_all_receivers = true;
  maximum_selectable_receivers = 0;
  questionnaire_id = "";
  additional_questionnaire_id = "";
  additional_questionnaires: string[] = [];
  score_threshold_medium = 0;
  score_threshold_high = 0;
  tip_reminder = 0;
  receivers = [];
  profiles = [];
}
