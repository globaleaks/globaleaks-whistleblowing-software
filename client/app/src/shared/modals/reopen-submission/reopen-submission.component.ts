import {Component, inject, ChangeDetectionStrategy} from "@angular/core";
import {NgbActiveModal, NgbModal, NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {FormsModule} from "@angular/forms";
import {TranslateModule} from "@ngx-translate/core";

@Component({
    changeDetection: ChangeDetectionStrategy.OnPush,
    selector: 'src-reopen-submission',
    templateUrl: './reopen-submission.component.html',
    standalone: true,
    imports: [
      FormsModule,
      NgbTooltipModule,
      TranslateModule
    ],
})
export class ReopenSubmissionComponent {
  private readonly modalService = inject(NgbModal);
  private readonly activeModal = inject(NgbActiveModal);

  confirmFunction: () => void;
    confirm() {
      this.confirmFunction();
      return this.activeModal.close();
    }

    cancel() {
      this.modalService.dismissAll();
    }
}
