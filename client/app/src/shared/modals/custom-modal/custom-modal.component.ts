import { Component, Input } from '@angular/core';
import { NgbActiveModal, NgbModal } from '@ng-bootstrap/ng-bootstrap';

@Component({
  selector: 'src-custom-modal',
  templateUrl: './custom-modal.component.html'
})
export class CustomModalComponent {

  @Input() arg: string;

  @Input() message: string;

  @Input() title: string;

  @Input() showInputText: boolean;

  inputText: string | null;

  

  constructor(private modalService: NgbModal, private activeModal: NgbActiveModal) {
  }

  confirmFunction: (secret: string, param?: any) => void;

  confirm(arg: string) {

    if(this.showInputText){
      this.confirmFunction(arg, this.inputText);
      return this.activeModal.close(arg);
    }

    this.confirmFunction(arg);
    return this.activeModal.close(arg);
    
  }

  cancel() {
    this.modalService.dismissAll();
  }

}
