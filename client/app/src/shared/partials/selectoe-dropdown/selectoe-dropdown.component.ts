import { Component, Input, OnInit } from '@angular/core';
import { Organization } from '@app/models/reciever/sendtip-data';

@Component({
  selector: 'src-selectoe-dropdown',
  templateUrl: './selectoe-dropdown.component.html'
})
export class SelectOEDropdownComponent{

  @Input() organizations: Organization[];

  selectedOrganization: string;

  addOrganization(event: Event) {
    const selectElement = event.target as HTMLSelectElement;
    this.selectedOrganization = selectElement.value;
  
  }
  

}
