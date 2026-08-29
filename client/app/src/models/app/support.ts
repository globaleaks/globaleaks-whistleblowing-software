export type SupportRequestStatus = "new" | "opened" | "closed";

export const supportRequestStatuses: SupportRequestStatus[] = ["new", "opened", "closed"];

export const supportRequestStatusLabels: Record<SupportRequestStatus, string> = {new: "New", opened: "Opened", closed: "Closed"};

export function supportRequestStatusClass(status: SupportRequestStatus): string {
  switch (status) {
    case "new":
      return "bg-info";
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
  progressive: number;
  creation_date: string;
  update_date: string;
  author_id: string | null;
  author_username: string;
  mail_address: string;
  status: SupportRequestStatus;
  preview: string;
  messages: SupportMessage[];
  key_available: boolean;
}

/**
 * Append to the local copy of the request the message just accepted by the
 * server, keeping in sync the fields the lists are rendered and sorted on.
 */
export function appendSupportMessage(request: SupportRequest, message: SupportMessage, status: SupportRequestStatus): void {
  request.messages = [...request.messages, message];
  request.preview = message.content;
  request.update_date = message.creation_date;
  request.status = status;
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
