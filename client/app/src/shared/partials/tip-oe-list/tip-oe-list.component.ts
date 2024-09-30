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
    this.utils.go('/sendtip-detail/018b675e-ac22-48b2-b8ea-0029fe22645a') //todo mockup   + item.tid);
  }

 
}
