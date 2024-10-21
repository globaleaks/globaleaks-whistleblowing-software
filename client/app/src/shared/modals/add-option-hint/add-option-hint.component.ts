import {Component, Input, inject} from "@angular/core";
import {NgbActiveModal, NgbModal} from "@ng-bootstrap/ng-bootstrap";
import {Option} from "@app/models/app/shared-public-model";
import {FormsModule} from "@angular/forms";
import {TranslateModule} from "@ngx-translate/core";
import {TranslatorPipe} from "@app/shared/pipes/translate";

@Component({
    selector: "src-add-option-hint",
    templateUrl: "./add-option-hint.component.html",
    standalone: true,
    imports: [FormsModule, TranslateModule, TranslatorPipe]
})
export class AddOptionHintComponent {
  private activeModal = inject(NgbActiveModal);
  private modalService = inject(NgbModal);

  confirmFunction: (data: Option) => void;
  @Input() arg: Option;

  confirm() {
    this.confirmFunction(this.arg);
    return this.activeModal.close(this.arg);
  }

  cancel() {
    this.modalService.dismissAll();
  }

}
