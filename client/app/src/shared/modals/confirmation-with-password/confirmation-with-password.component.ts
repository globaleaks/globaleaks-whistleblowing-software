import {Component, inject} from "@angular/core";
import {NgbActiveModal} from "@ng-bootstrap/ng-bootstrap";
import {FormsModule} from "@angular/forms";
import {TranslateModule} from "@ngx-translate/core";
import {TranslatorPipe} from "@app/shared/pipes/translate";

@Component({
    selector: "src-confirmation-with-password",
    templateUrl: "./confirmation-with-password.component.html",
    standalone: true,
    imports: [FormsModule, TranslateModule, TranslatorPipe]
})
export class ConfirmationWithPasswordComponent {
  private activeModal = inject(NgbActiveModal);

  secret: string;

  confirmFunction: (secret: string) => void;

  dismiss() {
    this.activeModal.dismiss();
  }

  confirm() {
    this.confirmFunction(this.secret);
    return this.activeModal.close(this.secret);
  }
}
