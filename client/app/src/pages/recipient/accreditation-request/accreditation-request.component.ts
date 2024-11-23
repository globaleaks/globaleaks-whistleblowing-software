import { Component } from "@angular/core";
import { EOInfo } from "@app/models/accreditor/organization-data";
import { HttpService } from "@app/shared/services/http.service";
import { Location } from '@angular/common'; 

@Component({
    selector: 'src-accreditation-request',
    templateUrl: './accreditation-request.component.html'
})
export class AccreditationRequestComponent {

    organizationInfo: EOInfo = {
        organization_name: '',
        organization_email: '',
        organization_institutional_site: '',
        organization_accreditation_reason: ''
    };
    isFormValid: boolean = false;

    constructor(private readonly httpService: HttpService, private readonly location: Location) {}

    onFormValidityChange(isValid: boolean) {
        this.isFormValid = isValid;
    }

    onSubmit() {
        if (this.isFormValid) {
            this.httpService.sendAccreditationRequest(this.organizationInfo).subscribe({
                next: () => {
                    this.location.back();
                },
                error: (err) => {
                  console.error("Errore durante la richiesta di aggiornamento", err);
                }
            }); 
        } else {
            console.log('Form is invalid');
        }
    }
}