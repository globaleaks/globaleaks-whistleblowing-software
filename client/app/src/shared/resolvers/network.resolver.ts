import {Injectable, inject} from "@angular/core";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {networkResolverModel} from "@app/models/resolvers/network-resolver-model";
import {ResourceResolver} from "@app/shared/resolvers/resource-resolver";

@Injectable({
  providedIn: "root"
})
export class NetworkResolver extends ResourceResolver<networkResolverModel> {
  private authenticationService = inject(AuthenticationService);

  constructor() {
    super("api/admin/network", new networkResolverModel());
  }

  protected allowed(): boolean {
    return this.authenticationService.session.role === "admin";
  }
}
