import { Injectable } from '@angular/core';
import { EOExtendedInfo } from '@app/models/accreditor/organization-data';
import { UtilsService } from '../services/utils.service';
import { HttpService } from '../services/http.service';
import { AuthenticationService } from '@app/services/helper/authentication.service';
import { map, Observable, of } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class AccreditationReqResolver {

  dataModel: EOExtendedInfo[] = [];

  constructor(private utilsService: UtilsService, private httpService: HttpService, 
    private authenticationService: AuthenticationService) {
  }


  
  reload() {
    this.httpService.accreditorRequestResource().subscribe(
      (response) => {
        this.dataModel = response;
        this.utilsService.reloadComponent();
      }
    );
  }

  resolve(): Observable<boolean> {
    if (this.authenticationService.session.role === "accreditor") {
      return this.httpService.accreditorRequestResource().pipe(
        map((response: EOExtendedInfo[]) => {
          this.dataModel = response;
          return true;
        })
      );
    }

    return of(true);
  }
}
