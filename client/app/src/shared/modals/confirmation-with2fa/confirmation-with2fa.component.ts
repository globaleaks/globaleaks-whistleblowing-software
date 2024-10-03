import {Component} from "@angular/core";
import {NgbActiveModal} from "@ng-bootstrap/ng-bootstrap";

@Component({
  selector: "src-confirmation-with2fa",
  templateUrl: "./confirmation-with2fa.component.html"
})
export class ConfirmationWith2faComponent {
  secret: string;

  constructor(private activeModal: NgbActiveModal) {
  }

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
