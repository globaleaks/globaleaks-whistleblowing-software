import {Data} from "@app/models/receiver/receiver-tip-data";

export interface rtipResolverModel {
  submissionStatusStr: string;
  context_name: string;
  context?: any;
  id: string;
  itip_id: string;
  creation_date: string;
  access_date: string;
  last_access: string;
  update_date: string;
  expiration_date: string;
  reminder_date: string;
  progressive: number;
  channel_progressive: number;
  channel_progressive_sort_key: string;
  context_count: number;
  slug: string;
  subscription: number;
  important: boolean;
  label: string;
  updated: boolean;
  context_id: string;
  type: string;
  allow_forward: boolean;
  can_request_forward: boolean;
  tor: boolean;
  questionnaire: any;
  answers: Answers;
  score: number;
  status: string;
  substatus: string;
  receiver_count: number;
  accessible: boolean;
  data: Data;
  receiver_ids: string[];
  receiver_names?: string;
}

export type Answers = Record<string, {
    required_status: boolean;
    value: string;
  }[]>;
