import {Component, OnInit, inject} from "@angular/core";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {LoginDataRef} from "@app/pages/auth/login/model/login-model";
import {ActivatedRoute, Router} from "@angular/router";
import {AppDataService} from "@app/app-data.service";
import {FormsModule} from "@angular/forms";

import {SimpleLoginComponent} from "./templates/simple-login/simple-login.component";
import {DefaultLoginComponent} from "./templates/default-login/default-login.component";
import {TranslateModule} from "@ngx-translate/core";
import {TranslatorPipe} from "@app/shared/pipes/translate";

import {OAuthService} from 'angular-oauth2-oidc';

@Component({
    selector: "app-login",
    templateUrl: "./login.component.html",
    standalone: true,
    imports: [FormsModule, SimpleLoginComponent, DefaultLoginComponent, TranslateModule, TranslatorPipe]
})
export class LoginComponent implements OnInit {
  private authentication = inject(AuthenticationService);
  router = inject(Router);
  private route = inject(ActivatedRoute);
  protected appDataService = inject(AppDataService);
  private oauthService = inject(OAuthService);

  protected readonly location = location;
  loginData = new LoginDataRef();

  constructor() {
    // When returning from the IDP the authorization response (code/state or error)
    // is carried in the query string and is still being processed asynchronously by
    // loadDiscoveryDocumentAndTryLogin(). Re-triggering the login flow here would
    // discard the pending code and bounce back to the IDP, so skip it in that case.
    const params = new URLSearchParams(window.location.search);
    const pendingAuthResponse = params.has("code") || params.has("error");

    if (this.appDataService.public.node.idp && !pendingAuthResponse && !this.oauthService.hasValidAccessToken() && !this.authentication.session) {
      this.oauthService.initLoginFlow();
    }
  }

  ngOnInit() {
    this.route.queryParams.subscribe(params => {
      if ("token" in params) {
        const token = params["token"];
        this.authentication.login(0, "", "", "", token);
      } else {
        if (this.authentication.session && this.authentication.session.role !== "whistleblower" && this.authentication.session.homepage) {
          this.router.navigateByUrl(this.authentication.session.homepage).then();
        }
      }
    });
  };
}
