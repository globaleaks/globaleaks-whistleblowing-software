import {Injectable, inject} from "@angular/core";
import {Router} from "@angular/router";
import {Observable, of} from "rxjs";
import {tap} from "rxjs/operators";
import {preferenceResolverModel} from "@app/models/resolvers/preference-resolver-model";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {ResourceResolver} from "@app/shared/resolvers/resource-resolver";

@Injectable({
  providedIn: "root"
})
export class PreferenceResolver extends ResourceResolver<preferenceResolverModel> {
  private readonly router = inject(Router);
  private readonly authenticationService = inject(AuthenticationService);

  constructor() {
    super("api/user/preferences", new preferenceResolverModel());
  }

  protected allowed(): boolean {
    return !!this.authenticationService.session;
  }

  // Preferences decide forced password change and 2FA redirects and are
  // read by components at construction: navigation waits for them.
  override resolve(): Observable<boolean> {
    if (!this.allowed()) {
      return of(true);
    }

    const url = this.router.currentNavigation()?.finalUrl?.toString() ?? this.router.url;

    return this.resolveAndWait().pipe(
      tap(() => {
        if (!url.startsWith("/action/")) {
          if (this.dataModel.password_change_needed) {
            this.router.navigate(["/action/forcedpasswordchange"]).then();
          } else if (this.dataModel.require_two_factor) {
            this.router.navigate(["/action/forcedtwofactor"]).then();
          }
        }
      })
    );
  }
}
