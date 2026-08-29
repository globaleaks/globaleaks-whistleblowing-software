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
  private httpService = inject(HttpService);
  private authenticationService = inject(AuthenticationService);

  dataModel: statisticalTemplateResolverModel[] = [];

  resolve(): Observable<boolean> {
    if (this.authenticationService.session.role === "analyst") {
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
