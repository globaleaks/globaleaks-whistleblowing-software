import { Injectable } from '@angular/core';
import { CanActivate,  Router } from '@angular/router';
import { AppDataService } from '@app/app-data.service';


@Injectable({
  providedIn: "root"
})
export class AccredRoutingGuard implements CanActivate {

  constructor(private router: Router, protected appDataService: AppDataService) {}

  canActivate(): boolean {
      const external_organization_activation = this.appDataService.public.node.external_organization_activation;
  
      if (!external_organization_activation) {
        this.router.navigate(['/']);
        return false;
      }
      else
        return true;
  }
}