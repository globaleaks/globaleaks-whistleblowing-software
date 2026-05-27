export class Session {
  id: string;
  role: string;
  encryption: boolean;
  user_id: string;
  properties: Properties;
  homepage: string;
  preferencespage: string;
  receipt: any;
  two_factor: boolean;
  permissions: { can_upload_files: boolean };
  token: any;
  redirect: string;
}

export interface Properties {
  management_session: any
  receipt_change_needed: boolean;
}

export class SessionRefresh {
  token: string;
}
