import {Injectable, inject} from "@angular/core";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {auditLogArea} from "@app/shared/partials/auditlog/auditlog-area";
import {jobResolverModel} from "@app/models/resolvers/job-resolver-model";
import {ResourceResolver} from "@app/shared/resolvers/resource-resolver";

@Injectable({
  providedIn: "root"
})
export class JobResolver extends ResourceResolver<jobResolverModel[]> {
  private readonly authenticationService = inject(AuthenticationService);

  constructor() {
    // The jobs are read on the area of the role in session: the administrator
    // and the auditor reach the same implementation, each on its own path
    super(`api/${auditLogArea(inject(AuthenticationService).session?.role ?? "")}/auditlog/jobs`, []);
  }

  protected allowed(): boolean {
    return !!auditLogArea(this.authenticationService.session?.role ?? "");
  }
}
