import { Component, OnInit, inject } from "@angular/core";
import {UtilsService} from "@app/shared/services/utils.service";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {AppDataService} from "@app/app-data.service";
import {AppConfigService} from "@app/services/root/app-config.service";

import { FormsModule } from "@angular/forms";
import { TranslateModule } from "@ngx-translate/core";
import { TranslatorPipe } from "@app/shared/pipes/translate";

@Component({
    selector: "src-receipt-whistleblower",
    templateUrl: "./receipt.component.html",
    standalone: true,
    imports: [FormsModule, TranslateModule, TranslatorPipe]
})
export class ReceiptComponent implements OnInit {
  private appConfigService = inject(AppConfigService);
  protected utilsService = inject(UtilsService);
  protected authenticationService = inject(AuthenticationService);
  protected appDataService = inject(AppDataService);

  receipt: string;
  receiptId: string = "";

  public ngOnInit(): void {
    if (this.authenticationService.session.receipt) {
      this.receipt = this.authenticationService.session.receipt;
    } else {
      this.receipt = this.appDataService.receipt;
    }
    this.receiptId = this.receipt.substring(0, 4) + " " + this.receipt.substring(4, 8) + " " + this.receipt.substring(8, 12) + " " + this.receipt.substring(12, 16);
  }

  viewReport() {
    this.appConfigService.setPage("tippage");
  }
}
