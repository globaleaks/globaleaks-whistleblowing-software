import {Component, inject} from "@angular/core";
import {NgbActiveModal} from "@ng-bootstrap/ng-bootstrap";
import {TranslateModule} from "@ngx-translate/core";

@Component({
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
