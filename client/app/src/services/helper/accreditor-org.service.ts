import { Injectable } from '@angular/core';
import { ExternalOrganization } from '@app/models/accreditor/organization-data';
import { HttpService } from '@app/shared/services/http.service';

@Injectable({
  providedIn: 'root'
})
export class AccreditorOrgService {

  organization: ExternalOrganization = new ExternalOrganization();

  constructor(private httpService: HttpService) { 

  }

  reset(){
    this.organization = new ExternalOrganization();
  }
}
