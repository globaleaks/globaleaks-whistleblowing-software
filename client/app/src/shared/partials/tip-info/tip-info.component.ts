import {Component, inject, input} from "@angular/core";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {WbtipService} from "@app/services/helper/wbtip.service";
import {AppDataService} from "@app/app-data.service";
import {UtilsService} from "@app/shared/services/utils.service";
import {ReceiverTipService} from "@app/services/helper/receiver-tip.service";
import {RecieverTipData} from "@app/models/receiver/receiver-tip-data";
import {DatePipe} from "@angular/common";
import {FormsModule} from "@angular/forms";
import {TranslateModule} from "@ngx-translate/core";
import {NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";


@Component({
    selector: "src-tip-info",
    templateUrl: "./tip-info.component.html",
    standalone: true,
    imports: [FormsModule, DatePipe, NgbTooltipModule, TranslateModule]
})
export class TipInfoComponent {
  protected authenticationService = inject(AuthenticationService);
  protected appDataService = inject(AppDataService);
  protected utilsService = inject(UtilsService);

  readonly tipService = input.required<ReceiverTipService | WbtipService>();
  readonly loading = input<boolean>();

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
    const tip = this.getReceiverTip();

    return !!tip?.data?.forward_request && (!!tip?.allow_forward || tip?.status === "closed");
  }

  forwardRequestStatusLabel() {
    if (!this.hasForwardRequestStatus()) {
      return "";
    }

    return this.getReceiverTip()?.allow_forward ? "Authorized" : "Denied";
  }
}
