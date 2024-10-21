import {Component, inject} from "@angular/core";
import {NgbActiveModal} from "@ng-bootstrap/ng-bootstrap";
import {UtilsService} from "@app/shared/services/utils.service";
import {PreferenceResolver} from "@app/shared/resolvers/preference.resolver";
import {TwoFactorAuthData} from "@app/services/helper/2fa.data.service";
import {Enable2fa} from "../../partials/enable-2fa/enable-2fa";
import {TranslateModule} from "@ngx-translate/core";
import {TranslatorPipe} from "@app/shared/pipes/translate";

@Component({
    selector: "src-enable2fa",
    templateUrl: "./enable2fa.component.html",
    standalone: true,
    imports: [Enable2fa, TranslateModule, TranslatorPipe]
})
export class Enable2faComponent {
  private preferenceResolver = inject(PreferenceResolver);
  private activeModal = inject(NgbActiveModal);
  private utilsService = inject(UtilsService);
  protected twoFactorAuthData = inject(TwoFactorAuthData);


  dismiss() {
    this.activeModal.dismiss();
  }

  confirm() {
    const requestObservable = this.utilsService.runUserOperation("enable_2fa", {
      "secret": this.twoFactorAuthData.totp.secret,
      "token": this.twoFactorAuthData.totp.token
    }, true);
    this.twoFactorAuthData.totp.token = ""
    requestObservable.subscribe(
      {
        next: _ => {
          this.preferenceResolver.dataModel.two_factor = true;
          this.activeModal.dismiss();
        },
        error: _ => {
          // this.utilsService.reloadCurrentRoute();
        }
      }
    );
  }
}
