import {Injectable, inject} from "@angular/core";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {contextResolverModel} from "@app/models/resolvers/context-resolver-model";
import {ResourceResolver} from "@app/shared/resolvers/resource-resolver";

@Injectable({
  providedIn: "root"
})
export class ContextsResolver extends ResourceResolver<contextResolverModel[]> {
  private readonly authenticationService = inject(AuthenticationService);

  constructor() {
    super("api/admin/contexts", []);
  }

  protected allowed(): boolean {
    return this.authenticationService.session?.role === "admin";
  }
}
