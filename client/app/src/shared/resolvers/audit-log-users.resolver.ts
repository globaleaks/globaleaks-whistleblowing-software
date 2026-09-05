import {Injectable, inject} from "@angular/core";
import {User} from "@app/models/resolvers/user-resolver-model";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {auditLogArea} from "@app/shared/partials/auditlog/auditlog-area";
import {ResourceResolver} from "@app/shared/resolvers/resource-resolver";

@Injectable({
  providedIn: "root"
})
export class AuditLogUsersResolver extends ResourceResolver<User[]> {
  private readonly authenticationService = inject(AuthenticationService);

  constructor() {
    // The users are read on the area of the role in session: the administrator
    // and the auditor reach the same implementation, each on its own path
    super(`api/${auditLogArea(inject(AuthenticationService).session.role)}/auditlog/users`, []);
  }

  protected allowed(): boolean {
    return !!auditLogArea(this.authenticationService.session.role);
  }
}
