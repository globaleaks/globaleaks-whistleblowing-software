import {Injectable, inject} from "@angular/core";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {notificationResolverModel} from "@app/models/resolvers/notification-resolver-model";
import {ResourceResolver} from "@app/shared/resolvers/resource-resolver";

@Injectable({
  providedIn: "root"
})
export class NotificationsResolver extends ResourceResolver<notificationResolverModel> {
  private authenticationService = inject(AuthenticationService);

  constructor() {
    super("api/admin/notification", new notificationResolverModel());
  }

  protected allowed(): boolean {
    return this.authenticationService.session.role === "admin";
  }
}
