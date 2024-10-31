import {Injectable, inject} from "@angular/core";
import {Observable, of} from "rxjs";
import {switchMap} from "rxjs/operators";
import {HttpService} from "@app/shared/services/http.service";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {contextResolverModel} from "@app/models/resolvers/context-resolver-model";

@Injectable({
  providedIn: "root"
})
export class ContextsResolver {
  private httpService = inject(HttpService);
  private authenticationService = inject(AuthenticationService);

  dataModel: contextResolverModel = new contextResolverModel();

  resolve(): Observable<boolean> {
    if (this.authenticationService.session.role === "admin") {
      return this.httpService.requestContextsResource().pipe(
        switchMap((response: contextResolverModel) => {
          this.dataModel = response;
          return of(true);
        })
      );
    }

    return of(true);
  }

}
