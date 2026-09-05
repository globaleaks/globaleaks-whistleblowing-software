import {Injectable, inject} from "@angular/core";
import {Observable, of} from "rxjs";
import {HttpService} from "@app/shared/services/http.service";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {map} from "rxjs/operators";
import {statisticalTemplateResolverModel} from "@app/models/resolvers/statistical-template-resolver-model";

@Injectable({
  providedIn: "root"
})
export class StatisticalTemplatesResolver {
  private readonly httpService = inject(HttpService);
  private readonly authenticationService = inject(AuthenticationService);

  dataModel: statisticalTemplateResolverModel[] = [];

  resolve(): Observable<boolean> {
    // The templates are read by the analysts, that are presented with them, and
    // by the administrators that compose them
    const role = this.authenticationService.session?.role;
    if (role === "analyst" || role === "admin") {
      return this.httpService.requestStatisticalTemplates().pipe(
        map((response) => {
          this.dataModel = response;
          return true;
        })
      );
    }
    return of(true);
  }
}
