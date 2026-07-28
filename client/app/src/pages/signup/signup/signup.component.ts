import {Component, OnInit, inject} from "@angular/core";
import {AppDataService} from "@app/app-data.service";
import {HttpService} from "@app/shared/services/http.service";
import {AppConfigService} from "@app/services/root/app-config.service";
import {Signup} from "@app/models/component-model/signup";
import {ActivatedRoute, Router} from "@angular/router";
import {HttpHeaders} from "@angular/common/http";
import {OAuthService} from "angular-oauth2-oidc";
import {IdpService} from "@app/services/root/idp.service";

import {SignupdefaultComponent} from "../templates/signupdefault/signupdefault.component";
import {WbpaComponent} from "../templates/wbpa/wbpa.component";
import {TranslateModule} from "@ngx-translate/core";
import {TranslatorPipe} from "@app/shared/pipes/translate";

@Component({
    selector: "src-signup",
    templateUrl: "./signup.component.html",
    standalone: true,
    imports: [SignupdefaultComponent, WbpaComponent, TranslateModule, TranslatorPipe]
})
export class SignupComponent implements OnInit {
  protected appDataService = inject(AppDataService);
  private httpService = inject(HttpService);
  private appConfig = inject(AppConfigService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private oauthService = inject(OAuthService);
  private idpService = inject(IdpService);

  hostname = "";
  completed = false;
  step = 1;
  idpRequired = false;
  idpAuthenticated = false;
  signup: Signup = {
    "subdomain": "",
    "name": "",
    "surname": "",
    "role": "",
    "email": "",
    "phone": "",
    "organization_name": "",
    "organization_type": "",
    "organization_tax_code": "",
    "organization_vat_code": "",
    "organization_location": "",
    "tos1": false,
    "tos2": false,
    "token": ""
  };

  ngOnInit() {
    this.appConfig.routeChangeListener();
    const queryParams = this.route.snapshot.queryParams;
    this.signup.token = "token" in queryParams ? queryParams["token"] : "";

    const config = this.appDataService.public?.node || {};
    this.idpRequired = !!config.idp;
    this.setIdpClaims();
    if (this.idpRequired) {
      this.oauthService.events.subscribe(() => this.setIdpClaims());
    }

    if (this.signup.token) {
      this.httpService.requestSignupInvite(this.signup.token).subscribe(invite => {
        this.signup.organization_name = invite.organization_name;
        this.signup.email = invite.email;
      });
    }
  }

  updateSubdomain() {
    this.signup.subdomain = "";
    if (this.signup.organization_name) {
      this.signup.subdomain = this.signup.organization_name.replace(/[^\w]/gi, "").toLowerCase().slice(0, 40);
    }
  }

  authenticateWithIDP() {
    this.idpService.startLogin(this.router.url);
  }

  setIdpClaims() {
    if (!this.idpRequired || !this.oauthService.hasValidAccessToken()) {
      return;
    }

    const claims = this.oauthService.getIdentityClaims() || {};
    this.idpAuthenticated = "sub" in claims || "user_id" in claims;

    if (claims["given_name"] && !this.signup.name) {
      this.signup.name = claims["given_name"];
    }
    if (claims["family_name"] && !this.signup.surname) {
      this.signup.surname = claims["family_name"];
    }
    if (claims["email"] && !this.signup.email) {
      this.signup.email = claims["email"];
    }
  }

  complete() {
    if (this.idpRequired && (!this.idpAuthenticated || !this.oauthService.hasValidAccessToken())) {
      this.authenticateWithIDP();
      return;
    }

    const param = JSON.stringify(this.signup);
    const accessToken = this.oauthService.getAccessToken();
    const headers = accessToken ? new HttpHeaders({Authorization: `Bearer ${accessToken}`}) : undefined;
    this.httpService.requestSignup(param, headers).subscribe
    (
      {
        next: _ => {
          this.step += 1;
        }
      }
    );
  }
}
