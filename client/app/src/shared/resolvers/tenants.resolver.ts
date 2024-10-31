import {Injectable, inject} from "@angular/core";
import {Observable, of} from "rxjs";
import {HttpService} from "@app/shared/services/http.service";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {tenantResolverModel} from "@app/models/resolvers/tenant-resolver-model";
import {catchError, map} from "rxjs/operators";

@Injectable({
  providedIn: "root"
})
export class TenantsResolver {
  private httpService = inject(HttpService);
  private authenticationService = inject(AuthenticationService);

  dataModel: tenantResolverModel = new tenantResolverModel();

  resolve(): Observable<boolean> {
    if (this.authenticationService.session.role === "admin") {
      return this.httpService.requestTenantsResource().pipe(
        map((response: tenantResolverModel) => {
          this.dataModel = response;
          return true;
        }),
        catchError(() => {
          return of(true);
        })
      );
    }
    return of(true);
  }
}
