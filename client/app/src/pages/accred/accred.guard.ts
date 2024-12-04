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
      const isAccreditationMode = this.appDataService.public.node.mode === 'accreditation';
  
      if (!isAccreditationMode) {
        this.router.navigate(['/']);
        return false;
      }
      else{
        this.appConfigService.setPage("accreditation-request")
        return true;
      }       
  }
}