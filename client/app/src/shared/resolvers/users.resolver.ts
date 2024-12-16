import {Injectable, inject} from "@angular/core";
import {Observable, of} from "rxjs";
import {HttpService} from "@app/shared/services/http.service";
import {userResolverModel} from "@app/models/resolvers/user-resolver-model";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {map} from "rxjs/operators";

@Injectable({
  providedIn: "root"
})
export class UsersResolver {
  private httpService = inject(HttpService);
  private authenticationService = inject(AuthenticationService);

  dataModel: userResolverModel;

  resolve(): Observable<boolean> {
    if (this.authenticationService.session.role === "admin") {
      return this.httpService.requestUsersResource().pipe(
        map((response: userResolverModel) => {
          this.dataModel = response;
          return true;
        })
      );
    }
    return of(true);
  }
}
