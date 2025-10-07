export class auditlogResolverModel {
  date: string;
  type: string;
  severity: number;
  user_id?: string;
  object_id?: string;
  data?: Data;
}

export class Data {
  status?: string;
  substatus?: string;
  prev_expiration_date?: number;
  curr_expiration_date?: number;
  recipient_id?: string;
  old_temporary_redaction?: any;
  new_temporary_redaction?: any;
  old_permanent_redaction?: any;
  permanent_redaction?: any;
  reminder_date?: number;
  file_type?: string;
  filename?: string;
  format?: string;
}