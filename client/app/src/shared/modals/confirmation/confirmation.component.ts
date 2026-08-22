import {Component, inject} from "@angular/core";
import {NgbActiveModal, NgbModal} from "@ng-bootstrap/ng-bootstrap";
import {TranslateModule} from "@ngx-translate/core";

@Component({
    selector: "src-confirmation",
    templateUrl: "./confirmation.component.html",
    standalone: true,
    imports: [TranslateModule]
})
export class ConfirmationComponent {
  private modalService = inject(NgbModal);
  private activeModal = inject(NgbActiveModal);

  arg: string;

  confirmFunction: (secret: string) => void;

  confirm(arg: string) {
    this.confirmFunction(arg);
    return this.activeModal.close(arg);
  }

  cancel() {
    this.modalService.dismissAll();
  }
}
