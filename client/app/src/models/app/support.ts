export type SupportRequestStatus = "new" | "read" | "answered" | "closed";

export const supportRequestStatuses: SupportRequestStatus[] = ["new", "read", "answered", "closed"];

export const supportRequestStatusLabels: Record<SupportRequestStatus, string> = {new: "New", read: "Read", answered: "Answered", closed: "Closed"};

export function supportRequestStatusClass(status: SupportRequestStatus): string {
  switch (status) {
    case "new":
      return "bg-info";
    case "answered":
      return "bg-success";
    case "closed":
      return "bg-dark";
    default:
      return "bg-secondary";
  }
}

export interface SupportMessage {
  id: string;
  creation_date: string;
  author_id: string | null;
  content: string;
  new: boolean;
}

export interface SupportRequest {
  id: string;
  tid: number;
  tenant_name: string;
  creation_date: string;
  update_date: string;
  author_id: string | null;
  mail_address: string;
  status: SupportRequestStatus;
  preview: string;
  messages: SupportMessage[];
  message_count: number;
  key_available: boolean;
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
