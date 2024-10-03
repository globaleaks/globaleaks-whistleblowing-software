import {Component} from "@angular/core";
import {NgbActiveModal} from "@ng-bootstrap/ng-bootstrap";

@Component({
  selector: "src-confirmation-with-password",
  templateUrl: "./confirmation-with-password.component.html"
})
export class ConfirmationWithPasswordComponent {
  secret: string;

  constructor(private activeModal: NgbActiveModal) {
  }

  confirmFunction: (secret: string) => void;

  dismiss() {
    this.activeModal.dismiss();
  }

  confirm() {
    this.confirmFunction(this.secret);
    return this.activeModal.close(this.secret);
  }
}
