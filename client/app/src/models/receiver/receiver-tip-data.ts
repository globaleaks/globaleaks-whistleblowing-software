import {
  Step,
  Children,
  RFile,
  WbFile,
  WhistleblowerIdentity,
  Comment
} from "@app/models/app/shared-public-model";
import {IarData} from "@app/models/receiver/iar-data";
import {RedactionData} from "@app/models/component-model/redaction";

export interface Questionnaire {
  steps: Step[];
  answers: Answers;
}

export interface ClosureQuestionnaire {
  steps: Step[];
  answers: Answers;
  date: string;
}

export class RecieverTipData {
  id: string;
  creation_date: string;
  update_date: string;
  expiration_date: string;
  progressive: number;
  context_id: string;
  type: string;
  allow_forward: boolean;
  can_forward: boolean;
  forward_receipt_valid: boolean;
  questionnaires: Questionnaire[];
  closure_questionnaire: ClosureQuestionnaire | null;
  closure_questionnaire_schema: any | null;
  tor: boolean;
  mobile: boolean;
  reminder_date: string;
  identity_provided: boolean;
  last_access: string;
  itip_last_access: string;
  counterpart_last_access: string;
  owned: boolean;
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
  questionnaire: Questionnaire;
  msg_receiver_selected: string | null;
  msg_receivers_selector: MsgReceiversSelector[];
  receivers_by_id: ReceiversById;
  submissionStatusStr: string;
  whistleblower_identity_field: Children;
  tip_id: string;
  redactions: RedactionData[];
  forwards: ForwardReport[];
  forwarding: ForwardingChannel | null;
}

export type Answers = Record<string, {
    required_status: boolean;
    value: string;
  }[]>;

export interface Receiver {
  id: string;
  name: string;
  active: boolean;
  last_access: string | null;
}

export interface ForwardReport {
  id: string;
  creation_date: string;
  target_tid: number;
  tenant_name: string;
  progressive: number;
  status: string;
  substatus: string;
  accessible: boolean;
}

export interface ForwardingChannel {
  from_tenant_name: string;
  to_tenant_name: string;
  update_date: string;
  messages_enabled: boolean;
  internaltip_id: string;
}

export interface WbForward {
  id: string;
  creation_date: string;
  update_date: string;
  tenant_name: string;
  status: string;
  substatus: string;
  messages_enabled: boolean;
}

export interface Data {
  whistleblower_identity_provided: boolean;
  whistleblower_identity: WhistleblowerIdentity;
  whistleblower_identity_date: string;
  forwarded_from?: {
    source_tid: number | string;
  };
  forward_request?: {
    source_tid: number | string;
  };
  forward_receipt?: string;
}

export interface Context {
  id: string;
  slug: string;
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
  questionnaire: Questionnaire;
}


export interface MsgReceiversSelector {
  key: string;
  value: string;
}

export type ReceiversById = Record<string, {
    name: string;
    active: boolean;
    last_access: string | null;
  }>;
