import {Component, inject, ChangeDetectionStrategy} from "@angular/core";
import {NgbActiveModal} from "@ng-bootstrap/ng-bootstrap";
import {TranslateModule} from "@ngx-translate/core";

@Component({
    changeDetection: ChangeDetectionStrategy.OnPush,
    selector: "src-enable-encryption",
    templateUrl: "./enable-encryption.component.html",
    standalone: true,
    imports: [TranslateModule]
})
export class EnableEncryptionComponent {
  protected activeModal = inject(NgbActiveModal);


  confirm() {
    this.activeModal.close();
  }

  cancel() {
    return this.activeModal.close();
  }
}
