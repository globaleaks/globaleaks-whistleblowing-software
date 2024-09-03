import { Injectable } from '@angular/core';
import { AccreditationRequestModel } from '@app/models/accreditor/organization-data';
import { UtilsService } from '../services/utils.service';
import { HttpService } from '../services/http.service';
import { AuthenticationService } from '@app/services/helper/authentication.service';
import { map, Observable, of } from 'rxjs';
import { AppDataService } from '@app/app-data.service';

@Injectable({
  providedIn: 'root'
})
export class AccreditationReqResolver {

  dataModel: AccreditationRequestModel[] = [];

  constructor(private utilsService: UtilsService, private httpService: HttpService, 
    private authenticationService: AuthenticationService,
    private appDataService: AppDataService) {
  }


  
  reload() {
    // this.httpService.accreditorRequestResource().subscribe(
    //   (response) => {
    //     this.dataModel = response;
    //     this.utilsService.reloadComponent();
    //   }
    // );

    //TODO MOCKUP
    setTimeout(()=> {
      this.utilsService.reloadComponent();
      this.appDataService.updateShowLoadingPanel(false)
    }, 1000)
  }

  resolve(): Observable<boolean> {
    if (this.authenticationService.session.role === "accreditor") {
      // return this.httpService.accreditorRequestResource().pipe(
      //   map((response: AccreditationRequestModel[]) => {
      //     this.dataModel = response;
      //     return true;
      //   })
      // );

      //TODO MOCKUP
      setTimeout(() => {
        this.dataModel = [        
          {
            id: "ID1",
            denomination: "ORGANIZZAZIONE 1",
            type: "NOT_AFFILIATED",
            state: "REQUESTED",
            accreditation_date: "10-08-2024",
            num_user_profiled: 10,
            num_tip: 5
          },
          {
            id: "ID2",
            denomination: "ORGANIZZAZIONE 2",
            type: "AFFILIATED",
            state: "INVITED",
            accreditation_date: "12-08-2024",
            num_user_profiled: 1,
            num_tip: 0
          },
          {
            id: "ID3",
            denomination: "ORGANIZZAZIONE 3",
            type: "NOT_AFFILIATED",
            state: "REJECTED",
            accreditation_date: "08-06-2024",
            num_user_profiled: 2,
            num_tip: 15
          }

        ]
        this.appDataService.updateShowLoadingPanel(false)
        return true;
      }, 1000)
    }

    return of(true);
  }
}
