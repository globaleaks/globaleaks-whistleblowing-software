import {Component, inject} from "@angular/core";
import {NgbModal, NgbModalRef, NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {ReceiverTipService} from "@app/services/helper/receiver-tip.service";
import {UtilsService} from "@app/shared/services/utils.service";
import {HttpService} from "@app/shared/services/http.service";
import {FormsModule} from "@angular/forms";
import {TranslateModule} from "@ngx-translate/core";


@Component({
    selector: "src-tip-operation-file-identity-access-request",
    templateUrl: "./tip-operation-file-identity-access-request.component.html",
    standalone: true,
    imports: [FormsModule, NgbTooltipModule, TranslateModule]
})
export class TipOperationFileIdentityAccessRequestComponent {
  private readonly modalService = inject(NgbModal);
  private readonly tipsService = inject(ReceiverTipService);
  private readonly httpService = inject(HttpService);
  private readonly utils = inject(UtilsService);

  request_motivation: string;
  modal: NgbModalRef;

  confirm() {
    this.modalService.dismissAll();
    this.httpService.requestIdentityAccess(this.tipsService.tip.id, this.request_motivation)
      .subscribe(
        () => {
          this.utils.reloadCurrentRoute();
        }
      );
  }

  reload() {
    this.utils.reloadCurrentRoute();
  }

  cancel() {
    this.modalService.dismissAll();
  }
}
