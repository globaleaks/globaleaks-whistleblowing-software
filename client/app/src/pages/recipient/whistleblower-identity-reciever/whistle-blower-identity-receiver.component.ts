import { Component, Input, inject } from "@angular/core";
import {NgbModal} from "@ng-bootstrap/ng-bootstrap";
import {ReceiverTipService} from "@app/services/helper/receiver-tip.service";
import {
  TipOperationFileIdentityAccessRequestComponent
} from "@app/shared/modals/tip-operation-file-identity-access-request/tip-operation-file-identity-access-request.ompoent";
import {HttpService} from "@app/shared/services/http.service";
import {UtilsService} from "@app/shared/services/utils.service";
import { NgClass, DatePipe } from "@angular/common";
import { TipFieldComponent } from "../../../shared/partials/tip-field/tip-field.component";
import { TranslateModule } from "@ngx-translate/core";
import { TranslatorPipe } from "@app/shared/pipes/translate";


@Component({
    selector: "src-whistleblower-identity-reciever",
    templateUrl: "./whistle-blower-identity-receiver.component.html",
    standalone: true,
    imports: [TipFieldComponent, NgClass, DatePipe, TranslateModule, TranslatorPipe]
})
export class WhistleBlowerIdentityReceiverComponent {
  protected tipService = inject(ReceiverTipService);
  protected utilsService = inject(UtilsService);
  private httpService = inject(HttpService);
  private modalService = inject(NgbModal);
  private utils = inject(UtilsService);

  @Input() redactOperationTitle: string;
  @Input() redactMode: boolean;
  collapsed: boolean = true;

  public toggleCollapse() {
    this.collapsed = !this.collapsed;
  }

  fileIdentityAccessRequest() {
    const modalRef = this.modalService.open(TipOperationFileIdentityAccessRequestComponent, {
      backdrop: 'static',
      keyboard: false
    });
    modalRef.componentInstance.tip = this.tipService.tip;
  }

  accessIdentity() {
    return this.httpService.accessIdentity(this.tipService.tip.id).subscribe(
      _ => {
        this.utils.reloadCurrentRoute();
      }
    );
  }
}
