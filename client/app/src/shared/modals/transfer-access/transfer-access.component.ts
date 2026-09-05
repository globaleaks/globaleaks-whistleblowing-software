import {Component, inject} from "@angular/core";
import {Receiver} from "@app/models/app/public-model";
import {NgbActiveModal} from "@ng-bootstrap/ng-bootstrap";
import {NgSelectComponent, NgLabelTemplateDirective} from "@ng-select/ng-select";
import {FormsModule} from "@angular/forms";
import {TranslateModule} from "@ngx-translate/core";

@Component({
    selector: "src-transfer-access",
    templateUrl: "./transfer-access.component.html",
    standalone: true,
    imports: [
        NgSelectComponent,
        FormsModule,
        NgLabelTemplateDirective,
        TranslateModule,
        ],
})
export class TransferAccessComponent {
  private readonly activeModal = inject(NgbActiveModal);

  usersNames: Record<string, string>;
  selectableRecipients: Receiver[];
  receiverId: { id: number };

  confirm(receiverId: { id: number }) {
    this.activeModal.close(receiverId.id);
  }

  cancel() {
    return this.activeModal.close();
  }
}
