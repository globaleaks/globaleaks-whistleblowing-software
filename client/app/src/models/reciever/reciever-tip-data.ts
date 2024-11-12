import {
  Step,
  TriggeredByOption,
  Children,
  RFile,
  WbFile,
  WhistleblowerIdentity,
  Comment
} from "@app/models/app/shared-public-model";
import {IarData} from "@app/models/reciever/Iar-data";
import {RedactionData} from "@app/models/component-model/redaction";

export class RecieverTipData {
  id: string;
  creation_date: string;
  update_date: string;
  expiration_date: string;
  progressive: number;
  context_id: string;
  questionnaires: Questionnaire[];
  tor: boolean;
  mobile: boolean;
  reminder_date: string;
  enable_whistleblower_identity: boolean;
  last_access: string;
  score: number;
  status: string;
  substatus: string;
  receivers: Receiver[];
  comments: Comment[];
  rfiles: RFile[];
  wbfiles: WbFile[];
  data: Data;
  internaltip_id: string;
  receiver_id: string;
  custodian: boolean;
  important: boolean;
  label: string;
  enable_notifications: boolean;
  iar: IarData;
  context: Context;
  questionnaire: Questionnaire3;
  msg_receiver_selected: string | null;
  msg_receivers_selector: MsgReceiversSelector[];
  receivers_by_id: ReceiversById;
  submissionStatusStr: string;
  whistleblower_identity_field: Children;
  tip_id: string;
  motivation: string;
  redactions: RedactionData[];
  forwardings: Forwarding[];
  max_eo_to_whistleblower_comments: number;
}

export interface Questionnaire {
  steps: Step[];
  answers: Answers;
}

export interface Answers {
  [key: string]: {
    required_status: boolean;
    value: string;
  }[];
}

export interface Receiver {
  id: string;
  name: string;
}

export interface Data {
  whistleblower_identity_provided: boolean;
  whistleblower_identity: WhistleblowerIdentity;
  whistleblower_identity_date: string;
}

export interface Context {
  id: string;
  hidden: boolean;
  order: number;
  tip_timetolive: number;
  tip_reminder: number;
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
  receivers: string[];
  picture: boolean;
  name: string;
  description: string;
  questionnaire: Questionnaire2;
}

export interface Questionnaire2 {
  id: string;
  editable: boolean;
  name: string;
  steps: Step2[];
}

export interface Step2 {
  id: string;
  questionnaire_id: string;
  order: number;
  triggered_by_score: number;
  triggered_by_options: TriggeredByOption[];
  children: Children2[];
  label: string;
  description: string;
}

export interface Children2 {
  id: string;
  instance: string;
  editable: boolean;
  type: string;
  template_id: string;
  template_override_id: string;
  step_id: string;
  fieldgroup_id: string;
  multi_entry: boolean;
  required: boolean;
  preview: boolean;
  attrs: Attrs2;
  x: number;
  y: number;
  width: number;
  triggered_by_score: number;
  triggered_by_options: TriggeredByOption2[];
  options: Option2[];
  children: Children[];
  label: string;
  description: string;
  hint: string;
  placeholder: string;
}

export interface Attrs2 {
  input_validation?: InputValidation2;
  max_len?: MaxLen2;
  min_len?: MinLen2;
  regexp?: Regexp2;
  display_alphabetically?: DisplayAlphabetically2;
}

export interface InputValidation2 {
  name: string;
  type: string;
  value: string;
}

export interface MaxLen2 {
  name: string;
  type: string;
  value: string;
}

export interface MinLen2 {
  name: string;
  type: string;
  value: string;
}

export interface Regexp2 {
  name: string;
  type: string;
  value: string;
}

export interface DisplayAlphabetically2 {
  name: string;
  type: string;
  value: boolean;
}

export interface TriggeredByOption2 {
  field: string;
  option: string;
  sufficient: boolean;
}

export interface Option2 {
  id: string;
  order: number;
  block_submission: boolean;
  score_points: number;
  score_type: string;
  trigger_receiver: string[];
  hint1: string;
  hint2: string;
  label: string;
}

export interface Questionnaire3 {
  id: string;
  editable: boolean;
  name: string;
  steps: Step3[];
}

export interface Step3 {
  id: string;
  questionnaire_id: string;
  order: number;
  triggered_by_score: number;
  triggered_by_options: TriggeredByOption[];
  children: Children3[];
  label: string;
  description: string;
  enabled: boolean;
}

export interface Children3 {
  id: string;
  instance: string;
  editable: boolean;
  type: string;
  template_id: string;
  template_override_id: string;
  step_id: string;
  fieldgroup_id: string;
  multi_entry: boolean;
  required: boolean;
  preview: boolean;
  attrs: Attrs3;
  x: number;
  y: number;
  width: number;
  triggered_by_score: number;
  triggered_by_options: TriggeredByOption3[];
  options: Option3[];
  children: Children[];
  label: string;
  description: string;
  hint: string;
  placeholder: string;
}

export interface Attrs3 {
  input_validation?: InputValidation3;
  max_len?: MaxLen3;
  min_len?: MinLen3;
  regexp?: Regexp3;
  display_alphabetically?: DisplayAlphabetically3;
}

export interface InputValidation3 {
  name: string;
  type: string;
  value: string;
}

export interface MaxLen3 {
  name: string;
  type: string;
  value: string;
}

export interface MinLen3 {
  name: string;
  type: string;
  value: string;
}

export interface Regexp3 {
  name: string;
  type: string;
  value: string;
}

export interface DisplayAlphabetically3 {
  name: string;
  type: string;
  value: boolean;
}

export interface TriggeredByOption3 {
  field: string;
  option: string;
  sufficient: boolean;
}

export interface Option3 {
  id: string;
  order: number;
  block_submission: boolean;
  score_points: number;
  score_type: string;
  trigger_receiver: string[];
  hint1: string;
  hint2: string;
  label: string;
}

export interface MsgReceiversSelector {
  key: string;
  value: string;
}

export interface ReceiversById {
  [key: string]: {
    name: string;
  };
}

export class Forwarding {
  id: string;
  tid: number;
  name: string;
  creation_date?: string;
  files: FileReference[];
  comments?: CommentReference[];
  state: string;
  questionnaire: Questionnaire;
}

export interface CommentReference {
  id: string;
  author_type: string;
}

export interface FileReference {
  id: string;
  author_type: string;
}