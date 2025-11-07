import {Component, inject} from "@angular/core";
import {NgbActiveModal, NgbModal, NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {FormsModule} from "@angular/forms";
import {TranslateModule} from "@ngx-translate/core";
import {TranslatorPipe} from "@app/shared/pipes/translate";

@Component({
    selector: 'src-reopen-submission',
    templateUrl: './reopen-submission.component.html',
    standalone: true,
    imports: [
      FormsModule,
      NgbTooltipModule,
      TranslateModule,
      TranslatorPipe
    ],
})
export class ReopenSubmissionComponent {
  private modalService = inject(NgbModal);
  private activeModal = inject(NgbActiveModal);

  confirmFunction: () => void;
    confirm() {
      this.confirmFunction();
      return this.activeModal.close();
    }

    cancel() {
      this.modalService.dismissAll();
    }
}
