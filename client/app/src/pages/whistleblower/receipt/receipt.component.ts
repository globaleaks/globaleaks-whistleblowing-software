import {Component, OnDestroy, OnInit, inject} from "@angular/core";
import {UtilsService} from "@app/shared/services/utils.service";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {AppDataService} from "@app/app-data.service";
import {AppConfigService} from "@app/services/root/app-config.service";
import {NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {FormsModule} from "@angular/forms";
import {TranslateModule} from "@ngx-translate/core";
import {TranslatorPipe} from "@app/shared/pipes/translate";

@Component({
    selector: "src-receipt-whistleblower",
    templateUrl: "./receipt.component.html",
    standalone: true,
    imports: [FormsModule, NgbTooltipModule, TranslateModule, TranslatorPipe]
})
export class ReceiptComponent implements OnInit, OnDestroy {
  private appConfigService = inject(AppConfigService);
  protected utilsService = inject(UtilsService);
  protected authenticationService = inject(AuthenticationService);
  protected appDataService = inject(AppDataService);

  receipt = "";
  receiptId = "";

  public ngOnInit(): void {
    this.receipt = this.authenticationService.session.receipt;
    this.authenticationService.session.receipt = undefined;
    this.receiptId = this.receipt.substring(0, 4) + " " + this.receipt.substring(4, 8) + " " + this.receipt.substring(8, 12) + " " + this.receipt.substring(12, 16);
  }

  public ngOnDestroy(): void {
    this.receipt = "";
    this.receiptId = "";
  }

  viewReport() {
    this.receipt = "";
    this.receiptId = "";
    this.appConfigService.setPage("tippage");
  }
}
