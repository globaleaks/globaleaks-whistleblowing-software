import { Injectable, inject } from "@angular/core";
import {Router, UrlTree} from "@angular/router";
import {Observable} from "rxjs";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {AppConfigService} from "@app/services/root/app-config.service";
import {UtilsService} from "@app/shared/services/utils.service";

@Injectable({
  providedIn: "root"
})
export class CustodianGuard {
  private utilsService = inject(UtilsService);
  private appConfigService = inject(AppConfigService);
  private router = inject(Router);
  authenticationService = inject(AuthenticationService);


  canActivate(): Observable<boolean | UrlTree> | Promise<boolean | UrlTree> | boolean | UrlTree {
    if (this.authenticationService.session) {
      if(this.authenticationService.session.role === "custodian"){
        this.appConfigService.setPage(this.router.url);
      }else {
        this.router.navigateByUrl("/login").then();
      }
      return true;
    } else {
      this.utilsService.routeGuardRedirect();
      return false;
    }
  }
}
