import { Injectable, inject } from "@angular/core";
import {Observable, map, of} from "rxjs";
import {HttpService} from "@app/shared/services/http.service";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {statusResolverModel} from "@app/models/resolvers/status-resolver-model";

@Injectable({
  providedIn: "root"
})
export class StatusResolver {
  private httpService = inject(HttpService);
  private authenticationService = inject(AuthenticationService);

  dataModel: statusResolverModel = new statusResolverModel();

  resolve(): Observable<boolean> {
    if (this.authenticationService.session.role === "admin") {
      return this.httpService.requestStatusesResource().pipe(
        map((response: statusResolverModel) => {
          this.dataModel = response;
          return true;
        })
      );
    }
    return of(true);
  }
}
