export type SupportRequestStatus = "new" | "read" | "answered" | "closed";

export interface SupportMessage {
  id: string;
  creation_date: string;
  author_id: string | null;
  content: string;
  new: boolean;
}

export interface SupportRequest {
  id: string;
  creation_date: string;
  update_date: string;
  author_id: string | null;
  mail_address: string;
  status: SupportRequestStatus;
  preview: string;
  messages: SupportMessage[];
  message_count: number;
  decryptable?: boolean;
  key_available?: boolean;
}

export interface NewSupportRequest {
  mail_address?: string;
  text: string;
}

export interface CreatedSupportRequest {
  id: string;
  status: SupportRequestStatus;
}

export interface NewSupportMessage {
  content: string;
}

export interface SupportRequestStatusUpdate {
  status: SupportRequestStatus;
}
