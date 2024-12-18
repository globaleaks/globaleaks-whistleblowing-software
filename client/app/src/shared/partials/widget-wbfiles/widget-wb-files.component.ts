import {Component, Input} from "@angular/core";
import { AppDataService } from "@app/app-data.service";
import { RFile, WbFile } from "@app/models/app/shared-public-model";
import {ReceiversById} from "@app/models/reciever/reciever-tip-data";
import {WbtipService} from "@app/services/helper/wbtip.service";
import {UtilsService} from "@app/shared/services/utils.service";

@Component({
  selector: "src-widget-wbfiles",
  templateUrl: "./widget-wb-files.component.html"
})
export class WidgetWbFilesComponent {

  @Input() index: number;
  @Input() ctx: string;
  @Input() receivers_by_id: ReceiversById;

  collapsed = false;
  submission = {};

  constructor(protected wbTipService: WbtipService, protected utilsService: UtilsService, private appDataService: AppDataService) {
  }

  public toggleCollapse() {
    this.collapsed = !this.collapsed;
  }

  listenToWbfiles(files: string) {
    this.utilsService.deleteResource(this.wbTipService.tip.rfiles, files);
  }

  getSortedRFiles(data: RFile[]): RFile[]{
    if(this.appDataService.public.node.antivirus_enabled)
      data = data.filter( f =>  f.status === 'VERIFIED' )

    return data;
  }


}
