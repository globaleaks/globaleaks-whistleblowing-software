export class tenantResolverModel {
  id: number;
  uuid: string;
  creation_date: string;
  active: boolean;
  hostname: string;
  mode: string;
  name: string;
  onionservice: string;
  rootdomain: string;
  subdomain: string;
  signup: any;
  profile: string;
  enable_forward_in: boolean;
  enable_forward_out: boolean;
  accept_forwarding: boolean;
  accept_forwarding_from: any[];
  accepts_requests_of_forward_from: any[];
  send_forwarding: any[];
  send_forwarding_request: any[];
  forward_filter: any[];
  forward_channel: string;
  forward_request_channel: string;
}
