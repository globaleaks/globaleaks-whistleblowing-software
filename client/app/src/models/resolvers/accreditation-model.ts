import { EOAdmin, EOPrimaryReceiver, ExternalOrganization } from "../app/shared-public-model";

export class AccreditationModel {
    check_privacy: boolean;
    external_organization: ExternalOrganization;
    admin: EOAdmin;
    primary_receiver: EOPrimaryReceiver;
}