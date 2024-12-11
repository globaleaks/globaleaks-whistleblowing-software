import {Step} from "@app/models/app/shared-public-model";

export class Root {
  node: Node;
  questionnaires: Questionnaire[];
  submission_statuses: Status[];
  receivers: Receiver[];
  contexts: Context[];
  proxy_idp_enabled: boolean;
}

export class Node {
  viewer: boolean;
  acme: boolean;
  timezone: number;
  allow_indexing: boolean;
  adminonly: boolean;
  pgp: boolean;
  custom_support_url: string;
  disable_admin_notification: boolean;
  disable_receiver_notification: boolean;
  disable_custodian_notification: boolean;
  default_language: string;
  default_questionnaire: string;
  description: string;
  disable_privacy_badge: boolean;
  disable_submissions: boolean = false;
  enable_custom_privacy_badge: boolean;
  enable_scoring_system: boolean;
  enable_signup: boolean;
  hostname: string;
  https_whistleblower: boolean = false;
  maximum_filesize: number;
  mode: string;
  name: string;
  onionservice: string;
  rootdomain: string;
  show_contexts_in_alphabetical_order: boolean;
  signup_tos1_enable: boolean;
  signup_tos2_enable: boolean;
  simplified_login: boolean;
  subdomain: string;
  wizard_done: boolean;
  contexts_clarification: string;
  custom_privacy_badge_text: string;
  disclaimer_text: string;
  footer: string;
  header_title_homepage: string;
  footer_whistleblowing_policy: string;
  presentation: string;
  signup_tos1_checkbox_label: string;
  signup_tos1_text: string;
  signup_tos1_title: string;
  signup_tos2_checkbox_label: string;
  signup_tos2_text: string;
  signup_tos2_title: string;
  whistleblowing_button: string;
  whistleblowing_question: string;
  root_tenant: boolean;
  languages_enabled: string[];
  languages_supported: LanguagesSupported[];
  script: boolean;
  css: string[];
  favicon: string[];
  logo: string[];
  footer_privacy_policy: string;
  user_privacy_policy_text: string;
  user_privacy_policy_url: string;
  forwarding_enabled: boolean;
  max_msg_external_to_whistle: number;
  max_msg_external_to_whistle_not_aff: number;
  antivirus_enabled: boolean;
  antivirus_clamd_ip: string;
  antivirus_clamd_port: number;
  proxy_idp_enabled: boolean;
  uuid: string;
  external: boolean;
}

export interface LanguagesSupported {
  code: string;
  name: string;
  native: string;
}

export interface Questionnaire {
  id: string;
  editable: boolean;
  name: string;
  steps: Step[];
}

export interface Status {
  id: string;
  order: number;
  system_defined: boolean;
  substatuses: Substatus[];
  label: string;
}

export interface Error {
  message: string,
  code: number,
  arguments: []
}

export interface Context {
  id: string;
  hidden: boolean;
  order: number;
  tip_timetolive: number;
  select_all_receivers: boolean;
  maximum_selectable_receivers: number;
  allow_recipients_selection: boolean;
  enable_comments: boolean;
  score_threshold_medium: number;
  score_threshold_high: number;
  show_receivers_in_alphabetical_order: boolean;
  show_steps_navigation_interface: boolean;
  questionnaire_id: string;
  additional_questionnaire_id: string;
  receivers: Receiver[];
  picture: boolean;
  name: string;
  description: string;
}

export interface Receiver {
  id: string;
  name: string;
  forcefully_selected: boolean;
  picture: boolean;
  description: string;
}

export interface Substatus {
  id: string;
  submissionstatus_id: string;
  order: number;
  label: string;
  tip_timetolive: number;
  tip_timetolive_option: number;
}
