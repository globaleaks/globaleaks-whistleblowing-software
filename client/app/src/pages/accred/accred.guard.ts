import { Injectable } from '@angular/core';
import { CanActivate,  Router } from '@angular/router';
import { AppDataService } from '@app/app-data.service';
import { AppConfigService } from '@app/services/root/app-config.service';


@Injectable({
  providedIn: "root"
})
export class AccredRoutingGuard implements CanActivate {

  constructor(private router: Router, protected appConfigService: AppConfigService, protected appDataService: AppDataService) {}

  canActivate(): boolean {
    // TODO mode 'accreditation' 
      // const external_organization_activation = this.appDataService.public.node.external_organization_activation;
  
      // if (!external_organization_activation) {
        this.router.navigate(['/']);
        return false;
      // }
      // else{
      //   this.appConfigService.setPage("accreditation-request")
      //   return true;
      // }
       
  }
}