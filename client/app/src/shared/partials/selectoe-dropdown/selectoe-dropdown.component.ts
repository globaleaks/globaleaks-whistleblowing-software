import { Component, EventEmitter, Input, Output } from '@angular/core';
import { tenantResolverModel } from '@app/models/resolvers/tenant-resolver-model';

@Component({
  selector: 'src-selectoe-dropdown',
  templateUrl: './selectoe-dropdown.component.html'
})
export class SelectOEDropdownComponent{

  @Input() organizations: tenantResolverModel[];
  @Output() dataToParent = new EventEmitter<number>();


  addOrganization(selectElement: HTMLSelectElement) {
    this.dataToParent.emit(parseInt(selectElement.value));
  }
  

}
