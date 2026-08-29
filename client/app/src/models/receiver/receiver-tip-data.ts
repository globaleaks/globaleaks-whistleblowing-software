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

export class RecieverTipData {
  id: string;
  creation_date: string;
  update_date: string;
  expiration_date: string;
  progressive: number;
  context_id: string;
  type: string;
  allow_transmission: boolean;
  can_communicate: boolean;
  can_decide_request: boolean;
  receipt_valid: boolean;
  questionnaires: Questionnaire[];
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
  exchanges: ExchangeReport[];
  exchange: ExchangeChannel | null;
}

export type Answers = Record<string, {
    required_status: boolean;
    value: string;
  }[]>;

export interface Receiver {
  id: string;
  name: string;
  // A report names, besides the recipients holding it, the ones that took part
  // in it and hold it no longer: only the former are active
  active: boolean;
  last_access: string | null;
}

export interface ExchangeReport {
  id: string;
  creation_date: string;
  target_tid: number;
  tenant_name: string;
  progressive: number;
  status: string;
  substatus: string;
  accessible: boolean;
}

export interface ExchangeChannel {
  type: string;
  from_tenant_name: string;
  to_tenant_name: string;
  update_date: string;
  internaltip_id: string;
}

export interface Data {
  whistleblower_identity_provided: boolean;
  whistleblower_identity: WhistleblowerIdentity;
  whistleblower_identity_date: string;
  transmitted_from?: {
    source_tid: number | string;
  };
  request?: {
    source_tid: number | string;
  };
  receipt?: string;
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
