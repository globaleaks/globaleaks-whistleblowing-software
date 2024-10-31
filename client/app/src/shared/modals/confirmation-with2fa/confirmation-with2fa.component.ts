import {Component, inject} from "@angular/core";
import {NgbActiveModal} from "@ng-bootstrap/ng-bootstrap";
import {FormsModule} from "@angular/forms";
import {TranslateModule} from "@ngx-translate/core";
import {TranslatorPipe} from "@app/shared/pipes/translate";

@Component({
    selector: "src-confirmation-with2fa",
    templateUrl: "./confirmation-with2fa.component.html",
    standalone: true,
    imports: [FormsModule, TranslateModule, TranslatorPipe]
})
export class ConfirmationWith2faComponent {
  private activeModal = inject(NgbActiveModal);

  secret: string;

  confirmFunction: (secret: string) => void;
  close: () => void;

  dismiss() {
    this.activeModal.close();
  }

  confirm() {
    this.confirmFunction(this.secret);
    this.activeModal.close(this.secret);
  }

}
