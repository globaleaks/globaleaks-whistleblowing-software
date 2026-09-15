import {Data} from "@app/models/receiver/receiver-tip-data";
import {SearchQuery} from "@app/models/search/search-query";

export interface rtipResolverModel {
  submissionStatusStr: string;
  reportModificationStr: string;
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
  subscription: number;
  important: boolean;
  label: string;
  updated: boolean;
  context_id: string;
  tor: boolean;
  questionnaire: any;
  answers: Answers;
  score: number;
  status: string;
  substatus: string;
  file_count: number;
  receiver_count: number;
  comment_count: number;
  accessible: boolean;
  data: Data;
  receiver_ids: string[];
  receiver_names?: string;
}

export type Answers = Record<string, {
    required_status: boolean;
    value: string;
  }[]>;

export interface RecipientReportsRequest {
  page: number;
  page_size: number;
  search: string;
  unread: boolean;
  sort: keyof rtipResolverModel;
  descending: boolean;
  query: SearchQuery;
}

export interface RecipientReportsPage {
  reports: rtipResolverModel[];
  page: number;
  page_size: number;
  total: number;
}
