import {redirectResolverModel} from "../resolvers/redirect-resolver-model";

export class Session {
  redirect: redirectResolverModel;
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
  t_type: number;
}

export interface Properties {
  management_session: any
  new_receipt: string;
}

export class SessionRefresh {
  token: string;
}
