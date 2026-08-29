import {Component, OnInit, inject} from "@angular/core";
import {AppDataService} from "@app/app-data.service";
import {HttpService} from "@app/shared/services/http.service";
import {AppConfigService} from "@app/services/root/app-config.service";
import {Signup} from "@app/models/component-model/signup";
import {ActivatedRoute, Router} from "@angular/router";

import {SignupdefaultComponent} from "../templates/signupdefault/signupdefault.component";
import {TranslateModule} from "@ngx-translate/core";

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

  hostname = "";
  completed = false;
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

    // The data compiled before the identification are restored, so that the
    // round trip towards the identity provider does not lose them; they are
    // kept in the session of the browser and never submitted until the
    // registration is completed
    this.restoreSignup();

    this.signup.token = "token" in queryParams ? queryParams["token"] : this.signup.token;
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

  complete() {
    this.submit();
  }

  private submit() {
    const param = JSON.stringify(this.signup);
    this.httpService.requestSignup(param).subscribe
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
