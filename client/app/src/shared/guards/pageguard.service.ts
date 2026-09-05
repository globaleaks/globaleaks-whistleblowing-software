import {Injectable, inject} from "@angular/core";
import {ActivatedRouteSnapshot, Router, RouterStateSnapshot, UrlTree} from "@angular/router";
import {Observable} from "rxjs";
import {AppDataService} from "@app/app-data.service";
import {AuthenticationService} from "@app/services/helper/authentication.service";

@Injectable({
  providedIn: "root"
})
export class Pageguard {
  private readonly authenticationService = inject(AuthenticationService);
  private readonly router = inject(Router);
  private readonly appDataService = inject(AppDataService);

  canActivate(_: ActivatedRouteSnapshot, state: RouterStateSnapshot): Observable<boolean | UrlTree> | Promise<boolean | UrlTree> | boolean | UrlTree {
    if (state.url === "/login") {
      if (this.authenticationService.session && this.authenticationService.session.role !=="whistleblower" && this.authenticationService.session.homepage) {
        void this.router.navigate([this.authenticationService.session.homepage]);
      }
    } else if (state.url === "/" || state.url === "/submission") {
      // The signup replaces the whistleblowing interface only when the
      // administrator elects it as the home of the platform
      if (this.appDataService.public.node && this.appDataService.public.node.enable_signup && this.appDataService.public.node.homepage === "/signup") {
        void this.router.navigate(["/signup"]);
      }
    }
    return true;
  }
}
