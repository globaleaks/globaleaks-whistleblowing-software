import { Component, Input, OnInit } from "@angular/core";
import { Forwarding } from "@app/models/reciever/reciever-tip-data";
import {UtilsService} from "@app/shared/services/utils.service";

@Component({
  selector: "src-tip-oe-list",
  templateUrl: "./tip-oe-list.component.html"
})
export class TipOeListComponent {

  @Input() forwardings: Forwarding[]

  collapsed = false;

  constructor(protected utils: UtilsService) {}

 
}
