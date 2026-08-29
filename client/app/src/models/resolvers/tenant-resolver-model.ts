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
  enable_forwarding_incoming: boolean;
  enable_forwarding_outgoing: boolean;
  require_forward_requests: boolean;
  accept_forwarding_from: any[];
  forward_channel: string;
  forward_request_channel: string;
}
