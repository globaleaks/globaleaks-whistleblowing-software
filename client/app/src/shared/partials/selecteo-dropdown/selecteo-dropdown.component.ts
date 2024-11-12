import { Component, EventEmitter, Input, Output } from '@angular/core';
import { Forwarding } from '@app/models/reciever/reciever-tip-data';

@Component({
  selector: 'src-selecteo-dropdown',
  templateUrl: './selecteo-dropdown.component.html'
})
export class SelectEODropdownComponent{

  @Input() organizations: Forwarding[];
  @Output() dataToParent = new EventEmitter<any>();

  toStr = JSON.stringify;


  addOrganization(selectElement: HTMLSelectElement) {
    this.dataToParent.emit(JSON.parse(selectElement.value));
  }
  

}
