import { HttpClient } from '@angular/common/http';
import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { AppDataService } from '@app/app-data.service';
import { EOExtendedInfo } from '@app/models/accreditor/organization-data';
import { AuthenticationService } from '@app/services/helper/authentication.service';
import { AppConfigService } from '@app/services/root/app-config.service';
import { AccreditationReqResolver } from '@app/shared/resolvers/accreditation-req-resolver.service';
import { HttpService } from '@app/shared/services/http.service';
import { UtilsService } from '@app/shared/services/utils.service';
import { TranslateService } from '@ngx-translate/core';
import { filter, orderBy } from 'lodash';

@Component({
  selector: 'src-organizations',
  templateUrl: './organizations.component.html'
})
export class OrganizationsComponent implements OnInit{

  constructor(private http: HttpClient,protected authenticationService: AuthenticationService, protected httpService: HttpService,
     private appConfigServices: AppConfigService, private router: Router, protected AReqs: AccreditationReqResolver, 
     protected utils: UtilsService, protected appDataService: AppDataService, private translateService: TranslateService) {

  }

  search: string | undefined;
  selectedReqs: string[] = [];
  filteredReqs: EOExtendedInfo[];
  currentPage: number = 1;
  itemsPerPage: number = 20;
  sortKey: string = "accreditation_date";
  sortReverse: boolean = true;



  ngOnInit(): void {
    if (!this.AReqs.dataModel) {
      this.router.navigate(["/accreditor/home"]).then();
    } else {
      this.filteredReqs = this.AReqs.dataModel;
    }
  }

  
  reload() {
    const reloadCallback = () => {
      this.AReqs.reload();
    };

    this.appConfigServices.localInitialization(true, reloadCallback);
  }


  onSearchChange(value: string | number | undefined) {
    if (typeof value !== "undefined") {
      this.currentPage = 1;
      this.filteredReqs = this.AReqs.dataModel;

      this.filteredReqs = orderBy(filter(this.filteredReqs, (req) =>
        Object.values(req).some((val) => {
          if (typeof val === "string" || typeof val === "number") {
            return String(val).toLowerCase().includes(String(value).toLowerCase());
          }
          return false;
        })
      ), "accreditation_date");
    }
  }

  orderbyCast(data: EOExtendedInfo[]): EOExtendedInfo[] {
    return data;
  }


}
