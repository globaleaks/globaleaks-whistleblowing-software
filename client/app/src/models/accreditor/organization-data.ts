export class ExternalOrganization {

    id: string;
    organization_name: string;
    organization_email: string;
    organization_institutional_site: string;
    admin_name: string;
    admin_surname: string;
    admin_fiscal_code: string;
    admin_email: string;

    recipient_name:string;
    recipient_surname:string;
    recipient_fiscal_code:string;
    recipient_email:string;
    
    type: string;
    state: string;

    tos1: boolean;
    tos2: boolean;
    
    accreditation_date: string;
    num_user_profiled: number;
    opened_tips: number;
    closed_tips: number;
    users: EOUser[];
}


export interface AccreditationRequestModel{
    id: string;
    denomination: string;
    type: string;
    state: string;
    accreditation_date: string;
    num_user_profiled: number;
    num_tip: number;
}

export interface EOExtendedInfo{
    id: string;
    organization_name: string;
    type: string;
    state: string;
    accreditation_date: string;
    num_user_profiled: number;
    opened_tips: number;
    closed_tips: number;
}


export interface EOInfo {
    organization_name: string;
    organization_email: string;
    organization_institutional_site: string;
  }
  
  
export interface EOAdmin {
    name: string;
    surname: string;
    email: string;
    fiscal_code: string;
}

export interface EOPrimaryReceiver {
    name: string;
    surname: string;
    email: string;
    fiscal_code: string;
}


export interface EOUser {
    id: string;
    creation_date: string;
    last_login: string;
    role: string;
    opened_rtips: number;
    closed_rtips: number;
}
