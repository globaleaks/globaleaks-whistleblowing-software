import { Component, EventEmitter, Input, Output } from "@angular/core";
import { Forwarding } from "@app/models/reciever/reciever-tip-data";
import {UtilsService} from "@app/shared/services/utils.service";

@Component({
  selector: "src-tip-eo-list",
  templateUrl: "./tip-eo-list.component.html"
})
export class TipEoListComponent {

  @Input() forwardings: Forwarding[]

  @Output() dataToParent = new EventEmitter<Forwarding>();

  collapsed = false;

  constructor(protected utils: UtilsService) {}

  goToDetailPage(item: Forwarding){
    this.dataToParent.emit(item)
  }

 
}
