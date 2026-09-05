import {Component, inject} from "@angular/core";
import {NgbModal} from "@ng-bootstrap/ng-bootstrap";
import {UtilsService} from "@app/shared/services/utils.service";
import {Receiver} from "@app/models/app/public-model";
import {cancelFun, ConfirmFunFunction} from "@app/shared/constants/types";
import {NgSelectComponent, NgLabelTemplateDirective} from "@ng-select/ng-select";
import {FormsModule} from "@angular/forms";
import {TranslateModule} from "@ngx-translate/core";


@Component({
    selector: "src-revoke-access",
    templateUrl: "./revoke-access.component.html",
    standalone: true,
    imports: [NgSelectComponent, FormsModule, NgLabelTemplateDirective, TranslateModule]
})
export class RevokeAccessComponent {
  private readonly modalService = inject(NgbModal);
  private readonly utils = inject(UtilsService);



  usersNames: Record<string, string>;
  selectableRecipients: Receiver[];
  confirmFun: ConfirmFunFunction;
  cancelFun: cancelFun;
  receiver_id: { id: number };

  confirm() {
    this.cancel();
    const confirmFun = this.confirmFun;
    if (confirmFun) {
      confirmFun(this.receiver_id);
    }
  }

  reload() {
    this.utils.reloadCurrentRoute();
  }

  cancel() {
    this.modalService.dismissAll();
  }
}
