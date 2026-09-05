import {Injectable, inject} from "@angular/core";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {statusResolverModel} from "@app/models/resolvers/status-resolver-model";
import {ResourceResolver} from "@app/shared/resolvers/resource-resolver";

@Injectable({
  providedIn: "root"
})
export class StatusResolver extends ResourceResolver<statusResolverModel> {
  private readonly authenticationService = inject(AuthenticationService);

  constructor() {
    super("api/admin/statuses", new statusResolverModel());
  }

  protected allowed(): boolean {
    return this.authenticationService.session.role === "admin";
  }
}
