import { Component, Input, inject } from "@angular/core";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {WbtipService} from "@app/services/helper/wbtip.service";
import {AppDataService} from "@app/app-data.service";
import {UtilsService} from "@app/shared/services/utils.service";
import {ReceiverTipService} from "@app/services/helper/receiver-tip.service";
import {HttpService} from "@app/shared/services/http.service";
import { DatePipe } from "@angular/common";
import { FormsModule } from "@angular/forms";
import { TranslateModule } from "@ngx-translate/core";
import { TranslatorPipe } from "@app/shared/pipes/translate";

@Component({
    selector: "src-tip-info",
    templateUrl: "./tip-info.component.html",
    standalone: true,
    imports: [FormsModule, DatePipe, TranslateModule, TranslatorPipe]
})
export class TipInfoComponent {
  protected authenticationService = inject(AuthenticationService);
  protected appDataService = inject(AppDataService);
  protected utilsService = inject(UtilsService);
  private rTipService = inject(ReceiverTipService);
  private httpService = inject(HttpService);

  @Input() tipService: ReceiverTipService | WbtipService;
  @Input() loading: boolean;

  markReportStatus(date: string) {
    const report_date = new Date(date);
    const current_date = new Date();
    return current_date > report_date;
  };

  updateLabel(label: string) {
    this.httpService.tipOperation("set", {"key": "label", "value": label}, this.rTipService.tip.id).subscribe(() => {
    });
  }
}
