import {Injectable, inject} from "@angular/core";
import {Observable, of} from "rxjs";
import {map} from "rxjs/operators";
import {HttpService} from "@app/shared/services/http.service";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {metricCatalogResolverModel} from "@app/models/resolvers/metric-catalog-resolver-model";

@Injectable({
  providedIn: "root"
})
export class StatisticalMetricsResolver {
  private httpService = inject(HttpService);
  private authenticationService = inject(AuthenticationService);

  dataModel: metricCatalogResolverModel = new metricCatalogResolverModel();

  resolve(): Observable<boolean> {
    const role = this.authenticationService.session.role;
    if (role === "analyst" || role === "admin") {
      return this.httpService.requestMetricCatalog().pipe(
        map((response) => {
          this.dataModel = response;
          return true;
        })
      );
    }
    return of(true);
  }
}
