import {Component, Input} from "@angular/core";
import {UtilsService} from "@app/shared/services/utils.service";
import {AppDataService} from "@app/app-data.service";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {HttpService} from "@app/shared/services/http.service";
import {NgbModal} from "@ng-bootstrap/ng-bootstrap";
import {ReceiverTipService} from "@app/services/helper/receiver-tip.service";
import {WbFile} from "@app/models/app/shared-public-model";
import {PreferenceResolver} from "@app/shared/resolvers/preference.resolver";
import {MaskService} from "@app/shared/services/mask.service";
import {RedactionData} from "@app/models/component-model/redaction";
import { Forwarding } from "@app/models/reciever/reciever-tip-data";

@Component({
  selector: "src-tip-files-receiver",
  templateUrl: "./tip-files-receiver.component.html"
})
export class TipFilesReceiverComponent {
  @Input() fileUploadUrl: string;
  @Input() redactMode: boolean;
  @Input() forwardings: Forwarding[];

  collapsed = false;

  constructor(protected maskService:MaskService,protected preferenceResolver:PreferenceResolver,protected modalService: NgbModal,protected httpService: HttpService, protected authenticationService: AuthenticationService, protected utilsService: UtilsService, protected tipService: ReceiverTipService, protected appDataService: AppDataService) {
  }


  getSortedWBFiles(data: WbFile[]): WbFile[] {
    return data;
  }

  redactFileOperation(operation: string, content_type: string, file: any) {
    const redactionData:RedactionData= {
      reference_id: file.ifile_id,
      internaltip_id: this.tipService.tip.id,
      entry: "0",
      operation: operation,
      content_type: content_type,
      temporary_redaction: [],
      permanent_redaction: [],
    };

    if (operation === 'full-mask') {
      redactionData.temporary_redaction = [{ start: '-inf', end: 'inf' }];
    }

    const redaction = this.maskService.getRedaction(file.ifile_id, '0', this.tipService.tip);

    if (redaction) {
      redactionData.id = redaction.id;
      this.tipService.updateRedaction(redactionData);
    } else {
      this.tipService.newRedaction(redactionData);
    }
  }


  checkForwarded(file: WbFile){

    let foundForwardedFiles = this.forwardings.filter(f => f.files?.some(i => i.id === file.ifile_id));

    return foundForwardedFiles.map(_ => _.name).join(', ');
  }
}

