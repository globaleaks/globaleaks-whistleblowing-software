import {Injectable, inject} from "@angular/core";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {tenantResolverModel} from "@app/models/resolvers/tenant-resolver-model";
import {ResourceResolver} from "@app/shared/resolvers/resource-resolver";

@Injectable({
  providedIn: "root"
})
export class TenantsResolver extends ResourceResolver<tenantResolverModel> {
  private authenticationService = inject(AuthenticationService);

  constructor() {
    super("api/admin/tenants", new tenantResolverModel());
  }

  protected allowed(): boolean {
    return this.authenticationService.session.role === "admin";
  }
}
