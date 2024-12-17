import { Injectable } from '@angular/core';
import { CanActivate,  Router } from '@angular/router';
import { AppDataService } from '@app/app-data.service';
import { AppConfigService } from '@app/services/root/app-config.service';


@Injectable({
  providedIn: "root"
})
export class AccredRoutingGuard implements CanActivate {

  constructor(protected appConfigService: AppConfigService, protected appDataService: AppDataService) {}

  canActivate(): boolean {

    this.appConfigService.setPage("accreditation-request")
    return true;
  }
}