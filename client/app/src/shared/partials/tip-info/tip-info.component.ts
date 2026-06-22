import {Component, Input, inject} from "@angular/core";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {WbtipService} from "@app/services/helper/wbtip.service";
import {AppDataService} from "@app/app-data.service";
import {UtilsService} from "@app/shared/services/utils.service";
import {ReceiverTipService} from "@app/services/helper/receiver-tip.service";
import {RecieverTipData} from "@app/models/receiver/receiver-tip-data";
import {DatePipe, NgClass} from "@angular/common";
import {FormsModule} from "@angular/forms";
import {TranslateModule} from "@ngx-translate/core";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";


@Component({
    selector: "src-tip-info",
    templateUrl: "./tip-info.component.html",
    standalone: true,
    imports: [FormsModule, DatePipe, NgClass, NgbTooltipModule, TranslateModule, TranslatorPipe]
})
export class TipInfoComponent {
  protected authenticationService = inject(AuthenticationService);
  protected appDataService = inject(AppDataService);
  protected utilsService = inject(UtilsService);

  @Input() tipService: ReceiverTipService | WbtipService;
  @Input() loading: boolean;

  markReportStatus(date: string) {
    const report_date = new Date(date);
    const current_date = new Date();
    return current_date > report_date;
  };

  getReceiverTip(): RecieverTipData | null {
    if (this.tipService instanceof ReceiverTipService) {
      return this.tipService.tip;
    }

    return null;
  }

  hasForwardRequestStatus() {
    return !!this.getReceiverTip()?.data?.forward_request;
  }

  forwardRequestStatusLabel() {
    if (!this.hasForwardRequestStatus()) {
      return "";
    }

    return this.getReceiverTip()?.type === "forward-request" ? "Pending" : "Authorized";
  }
}
