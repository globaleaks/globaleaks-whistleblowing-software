import {CollapsiblePanelComponent} from "@app/shared/components/collapsible-panel/collapsible-panel.component";
import {Component, inject, input} from "@angular/core";
import {NgbModal, NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {ReceiverTipService} from "@app/services/helper/receiver-tip.service";
import {
  TipOperationFileIdentityAccessRequestComponent
} from "@app/shared/modals/tip-operation-file-identity-access-request/tip-operation-file-identity-access-request.component";
import {HttpService} from "@app/shared/services/http.service";
import {UtilsService} from "@app/shared/services/utils.service";
import {DatePipe} from "@angular/common";
import {TipFieldComponent} from "@app/shared/partials/tip-field/tip-field.component";
import {TranslateModule} from "@ngx-translate/core";


@Component({
    selector: "src-whistleblower-identity-receiver",
    templateUrl: "./whistleblower-identity-receiver.component.html",
    standalone: true,
    imports: [CollapsiblePanelComponent, TipFieldComponent, NgbTooltipModule, DatePipe, TranslateModule]
})
export class WhistleBlowerIdentityReceiverComponent {
  protected tipService = inject(ReceiverTipService);
  protected utilsService = inject(UtilsService);
  private readonly httpService = inject(HttpService);
  private readonly modalService = inject(NgbModal);
  private readonly utils = inject(UtilsService);

  readonly redactOperationTitle = input<string>();
  readonly redactMode = input<boolean>();
  collapsed = false;

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
      () => {
        this.utils.reloadCurrentRoute();
      }
    );
  }
}
