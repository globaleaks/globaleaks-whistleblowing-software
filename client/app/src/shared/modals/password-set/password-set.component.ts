import {Component, inject} from "@angular/core";
import {NgbActiveModal, NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {UtilsService} from "@app/shared/services/utils.service";
import {TranslateModule} from "@ngx-translate/core";

@Component({
    selector: "src-password-set",
    templateUrl: "./password-set.component.html",
    standalone: true,
    imports: [NgbTooltipModule, TranslateModule]
})
export class PasswordSetComponent {
  private activeModal = inject(NgbActiveModal);
  protected utilsService = inject(UtilsService);

  password: string;

  protected visible = false;

  dismiss() {
    this.activeModal.dismiss();
  }
}
