import {Component, inject} from "@angular/core";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {PreferenceResolver} from "@app/shared/resolvers/preference.resolver";
import {AppDataService} from "@app/app-data.service";
import {HttpService} from "@app/shared/services/http.service";
import {Router} from "@angular/router";
import {ErrorCodes} from "@app/models/app/error-code";
import {FormsModule} from "@angular/forms";
import {PasswordStrengthValidatorDirective} from "../../directive/password-strength-validator.directive";
import {PasswordMeterComponent} from "../../components/password-meter/password-meter.component";
import {TranslateModule} from "@ngx-translate/core";
import {NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {CryptoService} from "@app/shared/services/crypto.service";

@Component({
    selector: "src-password-change",
    templateUrl: "./password-change.component.html",
    standalone: true,
    imports: [FormsModule, NgbTooltipModule, PasswordStrengthValidatorDirective, PasswordMeterComponent, TranslateModule]
})
export class PasswordChangeComponent {
  rootDataService = inject(AppDataService);
  private readonly authenticationService = inject(AuthenticationService);
  private readonly router = inject(Router);
  httpService = inject(HttpService);
  appDataService = inject(AppDataService);
  preferencesService = inject(PreferenceResolver);
  cryptoService = inject(CryptoService);

  passwordStrengthScore = 0;

  changePasswordArgs = {
    current: "",
    password: "",
    confirm: "",
  };

  async changePassword() {
    let current = this.changePasswordArgs.current;
    let password = this.changePasswordArgs.password;

    if (this.preferencesService.dataModel.salt) {
      this.appDataService.updateShowLoadingPanel(true);
      current = await this.cryptoService.hashArgon2(current, this.preferencesService.dataModel.salt);
      password = await this.cryptoService.hashArgon2(password, this.preferencesService.dataModel.salt);
      this.appDataService.updateShowLoadingPanel(false);
    }

    const data = {
      "operation": "change_password",
      "args": {
        current_password: current,
        new_password: password
      }
    };

    const forced = this.preferencesService.dataModel.password_change_needed;
    this.httpService.requestOperations(data).subscribe(
      {
        next: () => {
          this.preferencesService.dataModel.password_change_needed = false;
          this.resetForm();
          if (forced) {
            // Forced password changes block the user on the change-password
            // screen, so redirect to the homepage once completed.
            this.router.navigate([this.authenticationService.session.homepage]).then();
          }
        },
        error: (error) => {
          this.resetForm();
          this.rootDataService.errorCodes = new ErrorCodes(error.error["error_message"], error.error["error_code"], error.error.arguments);
          this.appDataService.updateShowLoadingPanel(false);
        }
      }
    );
  }

  resetForm() {
    this.changePasswordArgs = {current: "", password: "", confirm: ""};
    this.passwordStrengthScore = 0;
  }

  onPasswordStrengthChange(score: number) {
    this.passwordStrengthScore = score;
  }
}
