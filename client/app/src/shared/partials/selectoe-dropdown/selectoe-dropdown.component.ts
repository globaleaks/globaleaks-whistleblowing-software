import { Component, EventEmitter, Input, Output } from '@angular/core';
import { Forwarding } from '@app/models/reciever/reciever-tip-data';
import { tenantResolverModel } from '@app/models/resolvers/tenant-resolver-model';

@Component({
  selector: 'src-selectoe-dropdown',
  templateUrl: './selectoe-dropdown.component.html'
})
export class SelectOEDropdownComponent{

  @Input() organizations: Forwarding[];
  @Output() dataToParent = new EventEmitter<number>();


  addOrganization(selectElement: HTMLSelectElement) {
    this.dataToParent.emit(parseInt(selectElement.value));
  }
  

}
