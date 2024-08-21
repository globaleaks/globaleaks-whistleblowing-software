import { Injectable } from '@angular/core';
import { OrganizationData } from '@app/models/accreditor/organization-data';
import { HttpService } from '@app/shared/services/http.service';

@Injectable({
  providedIn: 'root'
})
export class AccreditorOrgService {

  organization: OrganizationData = new OrganizationData();

  constructor(private httpService: HttpService) { 

  }

  reset(){
    this.organization = new OrganizationData();
  }
}
