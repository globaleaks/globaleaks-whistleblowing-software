import {Component, inject} from "@angular/core";
import {NgbActiveModal} from "@ng-bootstrap/ng-bootstrap";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {TranslateModule} from "@ngx-translate/core";

@Component({
    selector: "src-update-available",
    templateUrl: "./update-available.component.html",
    standalone: true,
    imports: [TranslatorPipe, TranslateModule],
})
export class UpdateAvailableComponent {
  private activeModal = inject(NgbActiveModal);

  confirmFunction: () => void;

  confirm() {
    this.confirmFunction();
    return this.activeModal.close();
  }

  cancel() {
    return this.activeModal.close();
  }
}
