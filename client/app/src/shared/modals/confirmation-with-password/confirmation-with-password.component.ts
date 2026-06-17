import {Component, inject} from "@angular/core";
import {NgbActiveModal} from "@ng-bootstrap/ng-bootstrap";
import {FormsModule} from "@angular/forms";
import {TranslateModule} from "@ngx-translate/core";
import {AppDataService} from "@app/app-data.service";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {CryptoService} from "@app/shared/services/crypto.service";
import {PreferenceResolver} from "@app/shared/resolvers/preference.resolver";


@Component({
    selector: "src-confirmation-with-password",
    templateUrl: "./confirmation-with-password.component.html",
    standalone: true,
    imports: [FormsModule, TranslateModule, TranslatorPipe]
})
export class ConfirmationWithPasswordComponent {
  private activeModal = inject(NgbActiveModal);
  private cryptoService = inject(CryptoService);
  private preferencesService = inject(PreferenceResolver);
  private appDataService = inject(AppDataService);

  secret: string;

  confirmFunction: (secret: string) => void | Promise<void>;

  dismiss() {
    this.activeModal.dismiss();
  }

  async confirm() {
    let secret = this.secret;

    if (this.preferencesService.dataModel.salt) {
      this.appDataService.updateShowLoadingPanel(true);
      secret = await this.cryptoService.hashArgon2(secret, this.preferencesService.dataModel.salt);
      this.appDataService.updateShowLoadingPanel(false);
    }

    try {
      await this.confirmFunction(secret);
      this.activeModal.close(secret);
    } catch {
      // The confirmation was rejected (e.g. wrong password): keep the modal
      // open and let the operator try again.
      this.secret = "";
    }
  }
}
