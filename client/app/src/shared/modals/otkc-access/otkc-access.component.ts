import {Component, inject} from '@angular/core';
import {UtilsService} from '@app/shared/services/utils.service';
import {NgbModal, NgbTooltipModule} from '@ng-bootstrap/ng-bootstrap';
import {FormsModule} from '@angular/forms';
import {TranslateModule} from '@ngx-translate/core';

@Component({
    selector: 'src-otkc-access',
    templateUrl: './otkc-access.component.html',
    standalone: true,
    imports: [
        FormsModule,
        NgbTooltipModule,
        TranslateModule,
        ],
})
export class OtkcAccessComponent {
  private modalService = inject(NgbModal);
  protected utils = inject(UtilsService);

  arg: { receipt: any, formatted_receipt: any };

  confirmFunction: () => void;

  confirm() {
    this.confirmFunction();
    this.cancel();
  }

  cancel() {
    this.modalService.dismissAll();
  }
}
