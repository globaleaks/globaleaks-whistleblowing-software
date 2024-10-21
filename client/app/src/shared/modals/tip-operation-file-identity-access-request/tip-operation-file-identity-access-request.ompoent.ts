import {HttpClient} from "@angular/common/http";
import { Component, inject } from "@angular/core";
import {NgbModal, NgbModalRef} from "@ng-bootstrap/ng-bootstrap";
import {ReceiverTipService} from "@app/services/helper/receiver-tip.service";
import {UtilsService} from "@app/shared/services/utils.service";
import { FormsModule } from "@angular/forms";
import { TranslateModule } from "@ngx-translate/core";
import { TranslatorPipe } from "@app/shared/pipes/translate";


@Component({
    selector: "src-tip-operation-file-identity-access-request",
    templateUrl: "./tip-operation-file-identity-access-request.component.html",
    standalone: true,
    imports: [FormsModule, TranslateModule, TranslatorPipe]
})
export class TipOperationFileIdentityAccessRequestComponent {
  private modalService = inject(NgbModal);
  private tipsService = inject(ReceiverTipService);
  private http = inject(HttpClient);
  private utils = inject(UtilsService);

  request_motivation: string;
  modal: NgbModalRef;

  confirm() {
    this.modalService.dismissAll();
    this.http.post("api/recipient/rtips/" + this.tipsService.tip.id + "/iars", {"request_motivation": this.request_motivation})
      .subscribe(
        _ => {
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
