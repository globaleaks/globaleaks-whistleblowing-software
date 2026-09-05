import {Component, inject} from "@angular/core";
import {NgbActiveModal, NgbModal} from "@ng-bootstrap/ng-bootstrap";
import {Option} from "@app/models/app/shared-public-model";
import {FormsModule} from "@angular/forms";
import {TranslateModule} from "@ngx-translate/core";

@Component({
    selector: "src-add-option-hint",
    templateUrl: "./add-option-hint.component.html",
    standalone: true,
    imports: [FormsModule, TranslateModule]
})
export class AddOptionHintComponent {
  private readonly activeModal = inject(NgbActiveModal);
  private readonly modalService = inject(NgbModal);

  confirmFunction: (data: Option) => void;
  arg: Option;

  confirm() {
    this.confirmFunction(this.arg);
    return this.activeModal.close(this.arg);
  }

  cancel() {
    this.modalService.dismissAll();
  }

}
