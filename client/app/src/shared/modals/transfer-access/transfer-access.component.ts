import {Component, Input, inject} from "@angular/core";
import {Receiver} from "@app/models/app/public-model";
import {NgbActiveModal} from "@ng-bootstrap/ng-bootstrap";
import {NgSelectComponent, NgLabelTemplateDirective} from "@ng-select/ng-select";
import {FormsModule} from "@angular/forms";
import {TranslateModule} from "@ngx-translate/core";
import {TranslatorPipe} from "@app/shared/pipes/translate";

@Component({
    selector: "src-transfer-access",
    templateUrl: "./transfer-access.component.html",
    standalone: true,
    imports: [
        NgSelectComponent,
        FormsModule,
        NgLabelTemplateDirective,
        TranslateModule,
        TranslatorPipe,
    ],
})
export class TransferAccessComponent {
  private activeModal = inject(NgbActiveModal);

  @Input() usersNames: Record<string, string> | undefined;
  @Input() selectableRecipients: Receiver[];
  receiverId: { id: number };

  confirm(receiverId: { id: number }) {
    this.activeModal.close(receiverId.id);
  }

  cancel() {
    return this.activeModal.close();
  }
}
