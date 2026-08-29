export interface Signup {
  subdomain: string;
  name: string;
  surname: string;
  role: string;
  email: string;
  phone: string;
  organization_name: string;
  organization_email: string;
  organization_type: string;
  organization_tax_code: string;
  organization_vat_code: string;
  organization_location: string;
  tos1: boolean;
  tos2: boolean;
  token?: string;
}
