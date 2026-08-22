import {Injectable, inject} from "@angular/core";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {questionnaireResolverModel} from "@app/models/resolvers/questionnaire-model";
import {ResourceResolver} from "@app/shared/resolvers/resource-resolver";

@Injectable({
  providedIn: "root"
})
export class QuestionnairesResolver extends ResourceResolver<questionnaireResolverModel[]> {
  private authenticationService = inject(AuthenticationService);

  constructor() {
    super("api/admin/questionnaires", []);
  }

  protected allowed(): boolean {
    return this.authenticationService.session.role === "admin";
  }
}
