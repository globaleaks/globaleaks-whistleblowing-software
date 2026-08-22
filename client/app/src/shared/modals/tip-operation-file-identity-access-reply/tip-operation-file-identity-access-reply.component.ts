import {Component, inject} from "@angular/core";
import {NgbModal, NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {HttpService} from "@app/shared/services/http.service";
import {FormsModule} from "@angular/forms";
import {TranslateModule} from "@ngx-translate/core";

@Component({
    selector: "src-tip-operation-file-identity-access-reply",
    templateUrl: "./tip-operation-file-identity-access-reply.component.html",
    standalone: true,
    imports: [FormsModule, NgbTooltipModule, TranslateModule]
})
export class TipOperationFileIdentityAccessReplyComponent {
  private httpService = inject(HttpService);
  private modalService = inject(NgbModal);


  reply_motivation = "";
  iar_id = "";

  cancel() {
    this.modalService.dismissAll();
  }

  confirmFunction: () => void;

  confirm() {
    this.httpService.authorizeIdentity("api/custodian/iars/" + this.iar_id, {
      "reply": "denied",
      "reply_motivation": this.reply_motivation
    }).subscribe(
      {
        next: () => {
          this.confirmFunction();
        }
      }
    );
    this.cancel();
  }
}
