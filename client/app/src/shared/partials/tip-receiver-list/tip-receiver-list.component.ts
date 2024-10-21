import {Component, Input, inject} from "@angular/core";
import {UtilsService} from "@app/shared/services/utils.service";
import {WbtipService} from "@app/services/helper/wbtip.service";
import {ReceiverTipService} from "@app/services/helper/receiver-tip.service";
import {NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {TranslateModule} from "@ngx-translate/core";
import {TranslatorPipe} from "@app/shared/pipes/translate";

@Component({
    selector: "src-tip-receiver-list",
    templateUrl: "./tip-receiver-list.component.html",
    standalone: true,
    imports: [NgbTooltipModule, TranslateModule, TranslatorPipe]
})
export class TipReceiverListComponent {
  protected utilsService = inject(UtilsService);

  collapsed = false;
  @Input() tipService: ReceiverTipService | WbtipService;

  public toggleCollapse() {
    this.collapsed = !this.collapsed;
  }

}
