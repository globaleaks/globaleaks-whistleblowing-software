import {Injectable, inject} from "@angular/core";
import {Router} from "@angular/router";
import {Observable, of, throwError} from "rxjs";
import {PreferenceResolver} from "@app/shared/resolvers/preference.resolver";
import {nodeResolverModel} from "@app/models/resolvers/node-resolver-model";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {ResourceResolver} from "@app/shared/resolvers/resource-resolver";

@Injectable({
  providedIn: "root"
})
export class NodeResolver extends ResourceResolver<nodeResolverModel> {
  private readonly router = inject(Router);
  private readonly authenticationService = inject(AuthenticationService);
  private readonly preferenceResolver = inject(PreferenceResolver);

  constructor() {
    super("api/admin/node", new nodeResolverModel());
  }

  protected allowed(): boolean {
    const role = this.authenticationService.session?.role;

    return role === "admin" ||
      (role === "receiver" && this.preferenceResolver.dataModel.profile.permissions.can_manage_settings);
  }

  // The node configuration decides what the pages render: navigation
  // waits for it, as it did before.
  override resolve(): Observable<boolean> {
    return this.allowed() ? this.resolveAndWait() : of(true);
  }

  protected override onError(error: unknown): Observable<boolean> {
    this.authenticationService.deleteSession();
    void this.router.navigateByUrl("/login");
    return throwError(() => error);
  }
}
