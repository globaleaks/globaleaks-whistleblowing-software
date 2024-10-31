import {Injectable, inject} from "@angular/core";
import {Observable, of} from "rxjs";
import {HttpService} from "@app/shared/services/http.service";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {redirectResolverModel} from "@app/models/resolvers/redirect-resolver-model";
import {map} from "rxjs/operators";

@Injectable({
  providedIn: "root"
})
export class RedirectsResolver {
  private httpService = inject(HttpService);
  private authenticationService = inject(AuthenticationService);

  dataModel: redirectResolverModel[];

  resolve(): Observable<boolean> {
    if (this.authenticationService.session.role === "admin") {
      return this.httpService.requestRedirectsResource().pipe(
        map((response: redirectResolverModel[]) => {
          this.dataModel = response;
          return true;
        })
      );
    }
    return of(true);
  }
}
