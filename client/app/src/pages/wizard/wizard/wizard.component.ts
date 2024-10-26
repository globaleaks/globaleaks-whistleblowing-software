import {Component, OnInit, inject} from "@angular/core";
import {Constants} from "@app/shared/constants/constants";
import {Router} from "@angular/router";
import {HttpClient} from "@angular/common/http";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {HttpService} from "@app/shared/services/http.service";
import {AppDataService} from "@app/app-data.service";
import {TranslationService} from "@app/services/helper/translation.service";
import {AppConfigService} from "@app/services/root/app-config.service";
import {TitleService} from "@app/shared/services/title.service";
import {UtilsService} from "@app/shared/services/utils.service";
import {FormsModule} from "@angular/forms";
import {NgClass} from "@angular/common";
import {ProfileComponent} from "./template/profile/profile.component";
import {PasswordStrengthValidatorDirective} from "@app/shared/directive/password-strength-validator.directive";
import {PasswordMeterComponent} from "@app/shared/components/password-meter/password-meter.component";
import {TranslateModule} from "@ngx-translate/core";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";


@Component({
    selector: "src-wizard",
    templateUrl: "./wizard.component.html",
    standalone: true,
    imports: [FormsModule, NgbTooltipModule, NgClass, ProfileComponent, PasswordStrengthValidatorDirective, PasswordMeterComponent, TranslateModule, TranslatorPipe]
})
export class WizardComponent implements OnInit {
  private titleService = inject(TitleService);
  private translationService = inject(TranslationService);
  private router = inject(Router);
  private http = inject(HttpClient);
  private authenticationService = inject(AuthenticationService);
  private httpService = inject(HttpService);
  protected appDataService = inject(AppDataService);
  protected appConfigService = inject(AppConfigService);
  private utilsService = inject(UtilsService);

  step: number = 1;
  emailRegexp = Constants.emailRegexp;
  password_score = 0;
  admin_check_password = "";
  recipientDuplicate = false;
  recipient_check_password = "";
  tosAccept: boolean;
  license = "";
  completed = false;
  validation: { step2: boolean, step3: boolean, step4: boolean, step5: boolean, step6: boolean } = {
    step2: false,
    step3: false,
    step4: false,
    step5: false,
    step6: false
  };
  wizard = {
    "node_language": "en",
    "node_name": "",
    "admin_username": "",
    "admin_name": "",
    "admin_mail_address": "",
    "admin_password": "",
    "admin_escrow": true,
    "receiver_username": "",
    "receiver_name": "",
    "receiver_mail_address": "",
    "receiver_password": "",
    "skip_admin_account_creation": false,
    "skip_recipient_account_creation": false,
    "profile": "default",
    "enable_developers_exception_notification": false
  };

  ngOnInit() {
    if (this.appDataService.public.node.wizard_done) {
      this.router.navigate(["/"]).then(_ => {
      });
      return;
    }
    this.loadLicense();

    if (this.appDataService.pageTitle === "") {
      this.titleService.setTitle();
    }
  }

  complete() {
    if (this.completed) {
      return;
    }

    this.completed = true;

    this.wizard.node_language = this.translationService.language;

    const param = JSON.stringify(this.wizard);
    this.httpService.requestWizard(param).subscribe
    (
      {
        next: _ => {
          this.step += 1;
        }
      }
    );
  }

  validateDuplicateRecipient() {
    this.recipientDuplicate = this.wizard.receiver_username === this.wizard.admin_username;
    return this.recipientDuplicate;
  }

  goToAdminInterface() {
    const promise = () => {
      this.translationService.onChange(this.translationService.language);
      sessionStorage.removeItem("default_language");
      this.appConfigService.reinit(false);
      this.appConfigService.loadAdminRoute("/admin/home");
    };
    this.authenticationService.login(0, this.wizard.admin_username, this.wizard.admin_password, "", "", promise);
  }

  loadLicense() {
    this.http.get("license.txt", {responseType: "text"}).subscribe((data: string) => {
      this.license = data;
    });
  }

  onPasswordStrengthChange(score: number) {
    this.password_score = score;
  }

}
