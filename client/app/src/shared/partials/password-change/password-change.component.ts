import {Component, OnInit, inject} from "@angular/core";
import {HttpHeaders} from "@angular/common/http";
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
import {CryptoService} from "@app/shared/services/crypto.service";

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
  cryptoService = inject(CryptoService);

  passwordStrengthScore = 0;

  changePasswordArgs = {
    password: "",
    confirm: "",
  };

  async changePassword() {
    let password = this.changePasswordArgs.password;

    if (this.preferencesService.dataModel.salt) {
      this.appDataService.updateShowLoadingPanel(true);
      password = await this.cryptoService.hashArgon2(password, this.preferencesService.dataModel.salt);
      this.appDataService.updateShowLoadingPanel(false);
    }

    const data = {
      "operation": "change_password",
      "args": {password}
    };

    // Forced password changes (first login or password reset) do not require
    // confirmation of the current credential; voluntary changes do.
    if (this.preferencesService.dataModel.password_change_needed) {
      this.submitChangePassword(data);
    } else {
      this.utilsService.getConfirmation().subscribe((secret: string) => {
        const headers = new HttpHeaders({"X-Confirmation": this.utilsService.encodeString(secret)});
        this.submitChangePassword(data, headers);
      });
    }
  }

  private submitChangePassword(data: { operation: string, args: Record<string, string> }, headers?: HttpHeaders) {
    this.httpService.requestOperations(data, headers).subscribe(
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
