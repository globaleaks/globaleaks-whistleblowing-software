import {Component, OnInit, inject} from "@angular/core";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {PreferenceResolver} from "@app/shared/resolvers/preference.resolver";
import {UtilsService} from "@app/shared/services/utils.service";
import {AppDataService} from "@app/app-data.service";
import {HttpService} from "@app/shared/services/http.service";
import {Router} from "@angular/router";
import {ErrorCodes} from "@app/models/app/error-code";
import {FormsModule} from "@angular/forms";
import {NgClass} from "@angular/common";
import {PasswordStrengthValidatorDirective} from "../../directive/password-strength-validator.directive";
import {PasswordMeterComponent} from "../../components/password-meter/password-meter.component";
import {TranslateModule} from "@ngx-translate/core";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";


@Component({
    selector: "src-password-change",
    templateUrl: "./password-change.component.html",
    standalone: true,
    imports: [FormsModule, NgbTooltipModule, NgClass, PasswordStrengthValidatorDirective, PasswordMeterComponent, TranslateModule, TranslatorPipe]
})
export class PasswordChangeComponent implements OnInit {
  rootDataService = inject(AppDataService);
  private authenticationService = inject(AuthenticationService);
  private router = inject(Router);
  httpService = inject(HttpService);
  appDataService = inject(AppDataService);
  authentication = inject(AuthenticationService);
  preferencesService = inject(PreferenceResolver);
  utilsService = inject(UtilsService);

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

  ngOnInit() {
  };

  onPasswordStrengthChange(score: number) {
    this.passwordStrengthScore = score;
  }

}
