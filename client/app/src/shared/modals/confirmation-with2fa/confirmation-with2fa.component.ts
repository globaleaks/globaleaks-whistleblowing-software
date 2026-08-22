import {ChangeDetectorRef, Component, inject} from "@angular/core";
import {NgbActiveModal} from "@ng-bootstrap/ng-bootstrap";
import {FormsModule} from "@angular/forms";
import {TranslateModule} from "@ngx-translate/core";

@Component({
    selector: "src-confirmation-with2fa",
    templateUrl: "./confirmation-with2fa.component.html",
    standalone: true,
    imports: [FormsModule, TranslateModule]
})
export class ConfirmationWith2faComponent {
  private activeModal = inject(NgbActiveModal);
  private cdr = inject(ChangeDetectorRef);

  secret: string;
  error = false;

  confirmFunction: (secret: string) => void | Promise<void>;
  close: () => void;

  dismiss() {
    this.activeModal.close();
  }

  onInput() {
    // Clear the error marker as soon as the user starts editing the input.
    this.error = false;
  }

  async confirm() {
    try {
      await this.confirmFunction(this.secret);
      this.activeModal.close(this.secret);
    } catch {
      // The confirmation was rejected (e.g. wrong code): keep the modal open,
      // flag the input as invalid and let the operator try again.
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
