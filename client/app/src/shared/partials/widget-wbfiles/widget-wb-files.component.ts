import {Component, Input, inject} from "@angular/core";
import {ReceiversById} from "@app/models/receiver/receiver-tip-data";
import {WbtipService} from "@app/services/helper/wbtip.service";
import {UtilsService} from "@app/shared/services/utils.service";
import {NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {WbFilesComponent} from "../wbfiles/wb-files.component";
import {TranslateModule} from "@ngx-translate/core";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {OrderByPipe} from "@app/shared/pipes/order-by.pipe";

@Component({
    selector: "src-widget-wbfiles",
    templateUrl: "./widget-wb-files.component.html",
    standalone: true,
    imports: [NgbTooltipModule, WbFilesComponent, TranslateModule, TranslatorPipe, OrderByPipe]
})
export class WidgetWbFilesComponent {
  protected wbTipService = inject(WbtipService);
  protected utilsService = inject(UtilsService);


  @Input() index: number;
  @Input() ctx: string;
  @Input() receivers_by_id: ReceiversById;

  collapsed = false;
  submission = {};

  public toggleCollapse() {
    this.collapsed = !this.collapsed;
  }

  listenToWbfiles(files: string) {
    this.utilsService.deleteResource(this.wbTipService.tip.rfiles, files);
  }
}
