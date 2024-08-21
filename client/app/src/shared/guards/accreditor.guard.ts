import {Injectable} from "@angular/core";
import {Router, UrlTree} from "@angular/router";
import {Observable} from "rxjs";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {AppConfigService} from "@app/services/root/app-config.service";
import {UtilsService} from "@app/shared/services/utils.service";

@Injectable({
  providedIn: "root"
})
export class AccreditorGuard {
  constructor(private utilsService: UtilsService, private appConfigService: AppConfigService, private router: Router, public authenticationService: AuthenticationService) {
  }

  canActivate(): Observable<boolean | UrlTree> | Promise<boolean | UrlTree> | boolean | UrlTree {
    if (this.authenticationService.session) {
      if(this.authenticationService.session.role === "accreditor"){
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
