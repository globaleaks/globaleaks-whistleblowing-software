import { Component, Input, OnInit } from "@angular/core";
import { Forwarding } from "@app/models/reciever/reciever-tip-data";
import { ReceiverTipService } from "@app/services/helper/receiver-tip.service";
import {UtilsService} from "@app/shared/services/utils.service";

@Component({
  selector: "src-tip-oe-list",
  templateUrl: "./tip-oe-list.component.html"
})
export class TipOeListComponent {

  @Input() forwardings: Forwarding[]

  @Input() tipService: ReceiverTipService

  collapsed = false;

  constructor(protected utils: UtilsService) {}

  goToDetailPage(item: Forwarding){
    this.tipService.forwarding = item;
    this.utils.go('/sendtip-detail/016bab4f-829a-4556-865b-eb53ce36a925') //todo mockup anna  + item.tid);
  }

 
}
