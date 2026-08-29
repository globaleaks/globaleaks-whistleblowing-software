import {ChangeDetectorRef, Component, OnInit, inject} from "@angular/core";
import {AppDataService} from "@app/app-data.service";
import {HttpService} from "@app/shared/services/http.service";
import {AppConfigService} from "@app/services/root/app-config.service";
import {Signup} from "@app/models/component-model/signup";
import {ActivatedRoute, Router} from "@angular/router";
import {HttpHeaders} from "@angular/common/http";
import {OAuthService} from "angular-oauth2-oidc";
import {IdpService} from "@app/services/root/idp.service";

import {SignupdefaultComponent} from "../templates/signupdefault/signupdefault.component";
import {TranslateModule} from "@ngx-translate/core";
import {ErrorCodes} from "@app/models/app/error-code";

@Component({
    selector: "src-signup",
    templateUrl: "./signup.component.html",
    standalone: true,
    imports: [SignupdefaultComponent, TranslateModule]
})
export class SignupComponent implements OnInit {
  protected appDataService = inject(AppDataService);
  private httpService = inject(HttpService);
  private appConfig = inject(AppConfigService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private oauthService = inject(OAuthService);
  private idpService = inject(IdpService);
  private cdr = inject(ChangeDetectorRef);

  hostname = "";
  completed = false;
  show = false;
  step = 1;
  idpRequired = false;
  idpAuthenticated = false;
  idpFields = {name: false, surname: false};
  idpEmail = "";
  signup: Signup = {
    "subdomain": "",
    "name": "",
    "surname": "",
    "role": "",
    "email": "",
    "phone": "",
    "organization_name": "",
    "organization_email": "",
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

    // Data compiled before the identification are restored after the round trip to the identity
    // provider
    this.restoreSignup();

    this.signup.token = "token" in queryParams ? queryParams["token"] : this.signup.token;

    // The signup is authenticated against the IdP inherited from the profile
    // configured for the sites created via signup
    const config = this.appDataService.public?.node || {};
    this.idpRequired = !!config.signup_idp;
    this.setIdpClaims();
    if (this.idpRequired) {
      this.idpService.initialize("signup").then(() => this.setIdpClaims());
      this.oauthService.events.subscribe(() => this.setIdpClaims());
    }

    // A registration reachable by invitation only presents a completely blank
    // page when no invitation is carried or when the carried one is not valid
    if (!this.signup.token) {
      if (config.signup_invite_only) {
        window.location.replace("about:blank");
        return;
      }

      this.show = true;
    } else {
      this.httpService.requestSignupInvite(this.signup.token).subscribe({
        next: invite => {
          this.signup.organization_name = invite.organization_name;
          this.signup.organization_email = invite.organization_email;
          this.show = true;
          this.cdr.markForCheck();
        },
        error: () => {
          if (config.signup_invite_only) {
            this.appDataService.errorCodes = new ErrorCodes();
            window.location.replace("about:blank");
            return;
          }

          this.show = true;
          this.cdr.markForCheck();
        }
      });
    }
  }

  private getStorageKey(): string {
    const path = window.location.pathname || "";
    const match = path.match(/^\/t\/[^/]+/);
    return `signup:${match ? match[0] : "root"}`;
  }

  private storeSignup() {
    window.sessionStorage.setItem(this.getStorageKey(), JSON.stringify(this.signup));
  }

  private restoreSignup() {
    const stored = window.sessionStorage.getItem(this.getStorageKey());
    if (!stored) {
      return;
    }

    try {
      this.signup = {...this.signup, ...JSON.parse(stored)};
    } catch (_) {
      window.sessionStorage.removeItem(this.getStorageKey());
    }
  }

  private clearSignup() {
    window.sessionStorage.removeItem(this.getStorageKey());
  }

  authenticateWithIDP() {
    this.storeSignup();
    this.idpService.startLogin(this.router.url, "signup");
  }

  setIdpClaims() {
    if (!this.idpRequired || !this.oauthService.hasValidIdToken()) {
      return;
    }

    const claims = this.oauthService.getIdentityClaims() || {};
    this.idpAuthenticated = "sub" in claims || "user_id" in claims;

    // The data attested by the identity provider are presented to the user and
    // are not editable; the ones it does not publish are asked for as usual
    for (const [claim, key] of [["given_name", "name"], ["family_name", "surname"]] as const) {
      if (claims[claim]) {
        this.signup[key] = claims[claim];
        this.idpFields[key] = true;
      }
    }

    // The email published by the identity provider only prefills the form:
    // the user is free to be notified on a different address
    if (typeof claims["email"] === "string") {
      this.idpEmail = claims["email"];
    }

    // The claims land outside change detection (zoneless): request a refresh
    // so the unlocked form and the prefilled fields are rendered
    this.cdr.markForCheck();
  }

  complete() {
    if (!this.idpRequired) {
      this.submit();
      return;
    }

    // The session of the IdP used for the signup is restored before submitting,
    // as the site may be authenticated by a different identity provider
    this.idpService.initialize("signup").then(() => {
      this.setIdpClaims();

      if (!this.idpAuthenticated || !this.oauthService.hasValidIdToken()) {
        this.authenticateWithIDP();
        return;
      }

      this.submit();
    });
  }

  private submit() {
    const param = JSON.stringify(this.signup);
    const idToken = this.oauthService.getIdToken();
    const headers = idToken ? new HttpHeaders({Authorization: `Bearer ${idToken}`}) : undefined;
    this.httpService.requestSignup(param, headers).subscribe
    (
      {
        next: _ => {
          this.clearSignup();
          this.step += 1;
        }
      }
    );
  }
}
