import {Component, Input, OnInit, inject} from "@angular/core";
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
import {NgClass, DatePipe} from "@angular/common";
import {TranslateModule} from "@ngx-translate/core";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {ByteFmtPipe} from "@app/shared/pipes/byte-fmt.pipe";
import {OrderByPipe} from "@app/shared/pipes/order-by.pipe";
import {NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";


@Component({
    selector: "src-tip-files-receiver",
    templateUrl: "./tip-files-receiver.component.html",
    standalone: true,
    imports: [NgClass, DatePipe, TranslateModule, TranslatorPipe, ByteFmtPipe, OrderByPipe, NgbTooltipModule]
})
export class TipFilesReceiverComponent implements OnInit {
  protected maskService = inject(MaskService);
  protected preferenceResolver = inject(PreferenceResolver);
  protected modalService = inject(NgbModal);
  protected httpService = inject(HttpService);
  protected authenticationService = inject(AuthenticationService);
  protected utilsService = inject(UtilsService);
  protected tipService = inject(ReceiverTipService);
  protected appDataService = inject(AppDataService);

  @Input() fileUploadUrl: string;
  @Input() redactMode: boolean;

  collapsed = false;

  ngOnInit(): void {
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
}

