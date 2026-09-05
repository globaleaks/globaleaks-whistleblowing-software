import {Injectable, inject} from "@angular/core";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {statisticsResolverModel} from "@app/models/resolvers/statistics-resolver-model";
import {ResourceResolver} from "@app/shared/resolvers/resource-resolver";

@Injectable({
  providedIn: "root"
})
export class StatisticsResolver extends ResourceResolver<statisticsResolverModel> {
  private readonly authenticationService = inject(AuthenticationService);

  constructor() {
    super("api/analyst/stats", new statisticsResolverModel());
  }

  protected allowed(): boolean {
    return this.authenticationService.session?.role === "analyst";
  }
}
