import {Component, inject} from "@angular/core";
import {NgbActiveModal, NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {UtilsService} from "@app/shared/services/utils.service";
import {TranslateModule} from "@ngx-translate/core";

@Component({
    selector: "src-encryption-recovery-key",
    templateUrl: "./encryption-recovery-key.component.html",
    standalone: true,
    imports: [NgbTooltipModule, TranslateModule]
})
export class EncryptionRecoveryKeyComponent {
  private readonly activeModal = inject(NgbActiveModal);
  protected utilsService = inject(UtilsService);


  erk: string;

  protected visible = false;

  dismiss() {
    this.activeModal.dismiss();
  }
}
