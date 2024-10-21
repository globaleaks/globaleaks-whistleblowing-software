import {Component, Input, inject} from "@angular/core";
import {SubmissionStatus} from "@app/models/app/shared-public-model";
import {RecieverTipData} from "@app/models/receiver/receiver-tip-data";
import {NgbActiveModal, NgbModal} from "@ng-bootstrap/ng-bootstrap";
import {FormsModule} from "@angular/forms";

import {TranslateModule} from "@ngx-translate/core";
import {TranslatorPipe} from "@app/shared/pipes/translate";
@Component({
    selector: 'src-change-submission-status',
    templateUrl: './change-submission-status.component.html',
    standalone: true,
    imports: [
    FormsModule,
    TranslateModule,
    TranslatorPipe
],
})
export class ChangeSubmissionStatusComponent {
  private modalService = inject(NgbModal);
  private activeModal = inject(NgbActiveModal);

  @Input() arg: {tip:RecieverTipData, motivation:string,submission_statuses:SubmissionStatus[],status:any};
  
  confirmFunction: (status:SubmissionStatus,motivation: string) => void;
  
    confirm(status: SubmissionStatus,motivation:string) {
      if(status){
        this.confirmFunction(status,motivation);
        return this.activeModal.close(status);
      }else{
        this.cancel()
      }
    }
  
    cancel() {
      this.modalService.dismissAll();
    }
}
