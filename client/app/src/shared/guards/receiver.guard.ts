import {Injectable, inject} from "@angular/core";
import {Router, UrlTree} from "@angular/router";
import {Observable} from "rxjs";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {AppConfigService} from "@app/services/root/app-config.service";
import {UtilsService} from "@app/shared/services/utils.service";

@Injectable({
  providedIn: "root"
})
export class ReceiverGuard {
  private readonly utilsService = inject(UtilsService);
  private readonly appConfigService = inject(AppConfigService);
  private readonly router = inject(Router);
  authenticationService = inject(AuthenticationService);


  canActivate(): Observable<boolean | UrlTree> | Promise<boolean | UrlTree> | boolean | UrlTree {
    if (this.authenticationService.session) {
      if(["receiver", "transmitter"].includes(this.authenticationService.session.role)){
        this.appConfigService.setPage(this.router.url);
      } else {
        void this.router.navigateByUrl("/login");
      }
      return true;
    } else {
      this.utilsService.routeGuardRedirect();
      return false;
    }
  }
}
