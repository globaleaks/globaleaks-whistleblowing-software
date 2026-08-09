export class tenantResolverModel {
  id: number;
  uuid: string;
  creation_date: string;
  active: boolean;
  hostname: string;
  name: string;
  onionservice: string;
  rootdomain: string;
  subdomain: string;
  signup: any;
  profile: string;
  forwarding_relationships: any[];
  require_forward_requests: boolean;
  forward_source_access: boolean;
  contexts: any[];
  forward_channel: string;
  forward_request_channel: string;
}
