import { Component, OnInit, inject } from "@angular/core";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {LoginDataRef} from "@app/pages/auth/login/model/login-model";
import {ActivatedRoute, Router} from "@angular/router";
import {AppDataService} from "@app/app-data.service";
import { FormsModule } from "@angular/forms";

import { SimpleLoginComponent } from "./templates/simple-login/simple-login.component";
import { DefaultLoginComponent } from "./templates/default-login/default-login.component";
import { TranslateModule } from "@ngx-translate/core";
import { TranslatorPipe } from "@app/shared/pipes/translate";


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


  protected readonly location = location;
  loginData = new LoginDataRef();

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
