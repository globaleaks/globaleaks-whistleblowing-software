import {Injectable, inject} from "@angular/core";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {jobResolverModel} from "@app/models/resolvers/job-resolver-model";
import {ResourceResolver} from "@app/shared/resolvers/resource-resolver";

@Injectable({
  providedIn: "root"
})
export class JobResolver extends ResourceResolver<jobResolverModel[]> {
  private authenticationService = inject(AuthenticationService);

  constructor() {
    super("api/admin/auditlog/jobs", []);
  }

  protected allowed(): boolean {
    return this.authenticationService.session.role === "admin";
  }
}
