import { EOUser } from "../app/shared-public-model";

export class OrganizationData {

    id: string;
    denomination: string;
    type: string;
    state: string;
    accreditation_date: string;
    num_user_profiled: number;
    num_tip: number;
    users: EOUser[];
    pec: string;

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


