import {Component, Input} from "@angular/core";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {LoginDataRef} from "@app/pages/auth/login/model/login-model";
import {NgForm} from "@angular/forms";
import {AppDataService} from "@app/app-data.service";

@Component({
  selector: "app-simple-login",
  templateUrl: "./simple-login.component.html",
})
export class SimpleLoginComponent {

  @Input() loginData: LoginDataRef;
  @Input() loginValidator: NgForm;

  constructor(protected authentication: AuthenticationService, protected appDataService: AppDataService) {
  }


}
