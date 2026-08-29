import {Injectable, inject} from "@angular/core";
import {Observable, of} from "rxjs";
import {HttpService} from "@app/shared/services/http.service";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {map} from "rxjs/operators";
import {statisticalReportResolverModel} from "@app/models/resolvers/statistical-report-resolver-model";

@Injectable({
  providedIn: "root"
})
export class StatisticalReportsResolver {
  private httpService = inject(HttpService);
  private authenticationService = inject(AuthenticationService);

  dataModel: statisticalReportResolverModel[] = [];

  resolve(): Observable<boolean> {
    if (this.authenticationService.session.role === "analyst") {
      return this.httpService.requestStatisticalReports().pipe(
        map((response) => {
          this.dataModel = response;
          return true;
        })
      );
    }
    return of(true);
  }
}
