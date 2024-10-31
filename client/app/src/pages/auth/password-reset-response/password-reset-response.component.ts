import {Component, OnInit, inject} from "@angular/core";
import {PasswordRecoveryModel} from "@app/models/authentication/password-recovery-model";
import {ActivatedRoute, Router} from "@angular/router";
import {HttpService} from "@app/shared/services/http.service";
import {UtilsService} from "@app/shared/services/utils.service";
import {AppDataService} from "@app/app-data.service";
import {NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {FormsModule} from "@angular/forms";
import {TranslateModule} from "@ngx-translate/core";
import {TranslatorPipe} from "@app/shared/pipes/translate";

@Component({
    selector: "src-password-reset-response",
    templateUrl: "./password-reset-response.component.html",
    standalone: true,
    imports: [FormsModule, NgbTooltipModule, TranslateModule, TranslatorPipe]
})
export class PasswordResetResponseComponent implements OnInit {
  protected appDataService = inject(AppDataService);
  private route = inject(ActivatedRoute);
  private httpService = inject(HttpService);
  private router = inject(Router);
  protected utilsService = inject(UtilsService);

  state = "start";
  request = new PasswordRecoveryModel();

  submit() {
    const requestObservable = this.httpService.requestChangePassword(JSON.stringify({
      "reset_token": this.request.reset_token,
      "recovery_key": this.request.recovery_key,
      "auth_code": this.request.auth_code
    }));
    requestObservable.subscribe(
      {
        next: response => {

          if (response.status === "success") {
            this.router.navigate([("/login")], {queryParams: {token: response.token}}).then();
          } else {
            if (response.status === "require_recovery_key") {
              this.request.recovery_key = "";
            }
            this.request.auth_code = "";
            this.state = response.status;
          }
        }
      }
    );
  };

  ngOnInit(): void {
    this.request.reset_token = this.route.snapshot.queryParams["token"] || "";
    this.request.recovery_key = this.route.snapshot.queryParams["recovery"] || "";

    if (this.state === "start") {
      this.submit();
    }
  }
}
