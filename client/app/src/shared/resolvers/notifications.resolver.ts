import {Injectable, inject} from "@angular/core";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {
  notificationSettingsResolverModel,
  notificationTemplatesResolverModel,
  smtpResolverModel
} from "@app/models/resolvers/notification-resolver-model";
import {ResourceResolver} from "@app/shared/resolvers/resource-resolver";

// The notifications are read in four parts, each saved on its own: the settings, the templates
// and the two servers the mails are sent through

@Injectable({
  providedIn: "root"
})
export class NotificationSettingsResolver extends ResourceResolver<notificationSettingsResolverModel> {
  private readonly authenticationService = inject(AuthenticationService);

  constructor() {
    super("api/admin/notification/settings", new notificationSettingsResolverModel());
  }

  protected allowed(): boolean {
    return this.authenticationService.session?.role === "admin";
  }
}

@Injectable({
  providedIn: "root"
})
export class NotificationTemplatesResolver extends ResourceResolver<notificationTemplatesResolverModel> {
  private readonly authenticationService = inject(AuthenticationService);

  constructor() {
    super("api/admin/notification/templates", new notificationTemplatesResolverModel());
  }

  protected allowed(): boolean {
    return this.authenticationService.session?.role === "admin";
  }
}

@Injectable({
  providedIn: "root"
})
export class SMTP1Resolver extends ResourceResolver<smtpResolverModel> {
  private readonly authenticationService = inject(AuthenticationService);

  constructor() {
    super("api/admin/notification/smtp1", new smtpResolverModel());
  }

  protected allowed(): boolean {
    return this.authenticationService.session?.role === "admin";
  }
}

@Injectable({
  providedIn: "root"
})
export class SMTP2Resolver extends ResourceResolver<smtpResolverModel> {
  private readonly authenticationService = inject(AuthenticationService);

  constructor() {
    super("api/admin/notification/smtp2", new smtpResolverModel());
  }

  protected allowed(): boolean {
    return this.authenticationService.session?.role === "admin";
  }
}
