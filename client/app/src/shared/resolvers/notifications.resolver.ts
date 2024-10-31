import {Injectable, inject} from "@angular/core";
import {Observable, of} from "rxjs";
import {HttpService} from "@app/shared/services/http.service";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {notificationResolverModel} from "@app/models/resolvers/notification-resolver-model";
import {map} from "rxjs/operators";

@Injectable({
  providedIn: "root"
})
export class NotificationsResolver {
  private httpService = inject(HttpService);
  private authenticationService = inject(AuthenticationService);

  dataModel: notificationResolverModel = new notificationResolverModel();

  resolve(): Observable<boolean> {
    if (this.authenticationService.session.role === "admin") {
      return this.httpService.requestNotificationsResource().pipe(
        map((response: notificationResolverModel) => {
          this.dataModel = response;
          return true;
        })
      );
    }
    return of(true);
  }
}
