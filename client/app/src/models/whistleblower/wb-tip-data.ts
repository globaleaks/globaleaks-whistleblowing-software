import {RFile, WbFile, WhistleblowerIdentity, Comment} from "@app/models/app/shared-public-model";
import {Context, Answers, Questionnaire3, Questionnaire} from "@app/models/reciever/reciever-tip-data";
import {RedactionData} from "@app/models/component-model/redaction";

export class WbTipData {
  id: string;
  creation_date: string;
  update_date: string;
  expiration_date: string;
  progressive: number;
  context_id: string;
  questionnaires: Questionnaire[];
  enable_whistleblower_download: boolean;
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
  context: Context;
  questionnaire: Questionnaire3;
  additional_questionnaire: Questionnaire3;
  msg_receiver_selected: string | null;
  msg_receivers_selector: MsgReceiversSelector[];
  tip_id: string;
  receivers_by_id: ReceiversById;
  submissionStatusStr: string;
  label: string;
  fields: Children[];
  whistleblower_identity_field: Children;
  answers: Answers;
  motivation: string;
  redactions: RedactionData[];
  max_eo_to_whistleblower_comments: number;
}

export class Step {
  id: string;
  questionnaire_id: string;
  order: number;
  enabled = true;
  triggered_by_score: number;
  triggered_by_options: TriggeredByOption[];
  children: Children[];
  label: string;
  description: string;
}

export class Children {
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
  attrs: Attrs;
  x: number;
  y: number;
  width: number;
  triggered_by_score: number;
  triggered_by_options: TriggeredByOption[];
  options: Option[];
  children: Children[];
  label: string;
  description: string;
  hint: string;
  placeholder: string;
  enabled: boolean;
}

export class Attrs {
  input_validation?: InputValidation;
  max_len?: MaxLen;
  min_len?: MinLen;
  regexp?: Regexp;
}

export class InputValidation {
  name: string;
  type: string;
  value: string;
}

export class MaxLen {
  name: string;
  type: string;
  value: string;
}

export class MinLen {
  name: string;
  type: string;
  value: string;
}

export interface Regexp {
  name: string;
  type: string;
  value: string;
}

export class TriggeredByOption {
  field: string;
  option: string;
  sufficient: boolean;
}

export class Option {
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

export class Receiver {
  id: string;
  name: string;
}

export class Data {
  whistleblower_identity: WhistleblowerIdentity;
  whistleblower_identity_provided: boolean = false;
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