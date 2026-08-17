import {Injectable, inject} from "@angular/core";
import {User} from "@app/models/resolvers/user-resolver-model";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {ResourceResolver} from "@app/shared/resolvers/resource-resolver";

@Injectable({
  providedIn: "root"
})
export class AuditorUsersResolver extends ResourceResolver<User[]> {
  private authenticationService = inject(AuthenticationService);

  constructor() {
    super("api/auditor/auditlog/users", []);
  }

  protected allowed(): boolean {
    return this.authenticationService.session.role === "auditor";
  }
}
