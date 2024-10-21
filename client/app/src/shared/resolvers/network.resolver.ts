import { Injectable, inject } from "@angular/core";
import {Observable, of} from "rxjs";
import {HttpService} from "@app/shared/services/http.service";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {networkResolverModel} from "@app/models/resolvers/network-resolver-model";
import {map} from "rxjs/operators";

@Injectable({
  providedIn: "root"
})
export class NetworkResolver {
  private httpService = inject(HttpService);
  private authenticationService = inject(AuthenticationService);

  dataModel: networkResolverModel = new networkResolverModel();

  resolve(): Observable<boolean> {
    if (this.authenticationService.session.role === "admin") {
      return this.httpService.requestNetworkResource().pipe(
        map((response: networkResolverModel) => {
          this.dataModel = response;
          return true;
        })
      );
    }
    return of(true);
  }
}
