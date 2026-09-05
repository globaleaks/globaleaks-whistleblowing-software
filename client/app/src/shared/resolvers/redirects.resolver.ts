import {Injectable, inject} from "@angular/core";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {redirectResolverModel} from "@app/models/resolvers/redirect-resolver-model";
import {ResourceResolver} from "@app/shared/resolvers/resource-resolver";

@Injectable({
  providedIn: "root"
})
export class RedirectsResolver extends ResourceResolver<redirectResolverModel[]> {
  private readonly authenticationService = inject(AuthenticationService);

  constructor() {
    super("api/admin/redirects", []);
  }

  protected allowed(): boolean {
    return this.authenticationService.session.role === "admin";
  }
}
