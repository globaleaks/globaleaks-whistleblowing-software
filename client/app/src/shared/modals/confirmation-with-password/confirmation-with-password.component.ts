import {ChangeDetectorRef, Component, inject} from "@angular/core";
import {NgbActiveModal} from "@ng-bootstrap/ng-bootstrap";
import {FormsModule} from "@angular/forms";
import {TranslateModule} from "@ngx-translate/core";
import {AppDataService} from "@app/app-data.service";
import {CryptoService} from "@app/shared/services/crypto.service";
import {PreferenceResolver} from "@app/shared/resolvers/preference.resolver";


@Component({
    selector: "src-confirmation-with-password",
    templateUrl: "./confirmation-with-password.component.html",
    standalone: true,
    imports: [FormsModule, TranslateModule]
})
export class ConfirmationWithPasswordComponent {
  private readonly activeModal = inject(NgbActiveModal);
  private readonly cryptoService = inject(CryptoService);
  private readonly preferencesService = inject(PreferenceResolver);
  private readonly appDataService = inject(AppDataService);
  private readonly cdr = inject(ChangeDetectorRef);

  secret: string;
  error = false;

  confirmFunction: (secret: string) => void | Promise<void>;

  dismiss() {
    this.activeModal.dismiss();
  }

  onInput() {
    // Clear the error marker as soon as the user starts editing the input.
    this.error = false;
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
      // open, flag the input as invalid and let the operator try again.
      this.error = true;
    } finally {
      // Clear the secret from the form after every attempt, whether the
      // confirmation succeeded or failed, so it is not left in memory/UI.
      this.secret = "";
      // The continuation runs outside change detection (zoneless): request a
      // refresh so the cleared input and the error marker are rendered.
      this.cdr.markForCheck();
    }
  }
}
