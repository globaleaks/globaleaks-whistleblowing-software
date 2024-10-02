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
    this.utils.go('/sendtip-detail/90c4a81f-d5f0-464f-89db-b7685e140a02') //todo mockup   + item.tid);
  }

 
}
