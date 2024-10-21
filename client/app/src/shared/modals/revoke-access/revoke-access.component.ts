import { Component, Input, inject } from "@angular/core";
import {NgbModal} from "@ng-bootstrap/ng-bootstrap";
import {UtilsService} from "@app/shared/services/utils.service";
import {Receiver} from "@app/models/app/public-model";
import {cancelFun, ConfirmFunFunction} from "@app/shared/constants/types";
import { NgSelectComponent, NgLabelTemplateDirective } from "@ng-select/ng-select";
import { FormsModule } from "@angular/forms";
import { TranslateModule } from "@ngx-translate/core";
import { TranslatorPipe } from "@app/shared/pipes/translate";


@Component({
    selector: "src-revoke-access",
    templateUrl: "./revoke-access.component.html",
    standalone: true,
    imports: [NgSelectComponent, FormsModule, NgLabelTemplateDirective, TranslateModule, TranslatorPipe]
})
export class RevokeAccessComponent {
  private modalService = inject(NgbModal);
  private utils = inject(UtilsService);



  @Input() usersNames: Record<string, string> | undefined;
  @Input() selectableRecipients: Receiver[];
  @Input() confirmFun: ConfirmFunFunction;
  @Input() cancelFun: cancelFun;
  receiver_id: { id: number };

  confirm() {
    this.cancel();
    if (this.confirmFun) {
      this.confirmFun(this.receiver_id);
    }
  }

  reload() {
    this.utils.reloadCurrentRoute();
  }

  cancel() {
    this.modalService.dismissAll();
  }
}
