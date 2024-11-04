import {Component} from "@angular/core";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {PreferenceResolver} from "@app/shared/resolvers/preference.resolver";
import {UtilsService} from "@app/shared/services/utils.service";
import {AppDataService} from "@app/app-data.service";
import {HttpService} from "@app/shared/services/http.service";
import {Router} from "@angular/router";
import {ErrorCodes} from "@app/models/app/error-code";

@Component({
  selector: "src-password-change",
  templateUrl: "./password-change.component.html"
})
export class PasswordChangeComponent {
  passwordStrengthScore: number = 0;

  changePasswordArgs = {
    current: "",
    password: "",
    confirm: ""
  };

  changePassword() {
    const data = {
      "operation": "change_password",
      "args": this.changePasswordArgs
    };
    const requestObservable = this.httpService.requestOperations(data);
    requestObservable.subscribe(
      {
        next: _ => {
          this.preferencesService.dataModel.password_change_needed = false;
          this.router.navigate([this.authenticationService.session.homepage]).then();
        },
        error: (error) => {
          this.passwordStrengthScore = 0;
          this.rootDataService.errorCodes = new ErrorCodes(error.error["error_message"], error.error["error_code"], error.error.arguments);
          this.appDataService.updateShowLoadingPanel(false);
          return this.passwordStrengthScore;
        }
      }
    );
  }


  onPasswordStrengthChange(score: number) {
    this.passwordStrengthScore = score;
  }

  public constructor(public rootDataService: AppDataService, private authenticationService: AuthenticationService, private router: Router, public httpService: HttpService, public appDataService: AppDataService, public authentication: AuthenticationService, public preferencesService: PreferenceResolver, public utilsService: UtilsService) {

  }

}
