import {Component, inject} from "@angular/core";
import {NgbActiveModal, NgbModal} from "@ng-bootstrap/ng-bootstrap";
import {TranslateModule} from "@ngx-translate/core";
import {FormsModule} from "@angular/forms";
import {Constants} from "@app/shared/constants/constants";

@Component({
  selector: 'src-send-mail',
  templateUrl: './send-mail.component.html',
  standalone: true,
  imports: [FormsModule, TranslateModule],
})
export class SendMailComponent {
  private modalService = inject(NgbModal);
  private activeModal = inject(NgbActiveModal);
  protected readonly Constants = Constants;

  to_mail_address: string;

  confirmFunction: (to_mail_address: string) => void;

  confirm() {
    this.confirmFunction(this.to_mail_address);
    return this.activeModal.close();
  }

  cancel() {
    this.modalService.dismissAll();
  }
}
