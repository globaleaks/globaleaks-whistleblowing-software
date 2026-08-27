import {Component, Input, OnDestroy, OnInit, inject} from "@angular/core";
import {UtilsService} from "@app/shared/services/utils.service";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {AppDataService} from "@app/app-data.service";
import {AppConfigService} from "@app/services/root/app-config.service";
import {NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {FormsModule} from "@angular/forms";
import {TranslateModule} from "@ngx-translate/core";

@Component({
    selector: "src-receipt-whistleblower",
    templateUrl: "./receipt.component.html",
    standalone: true,
    imports: [FormsModule, NgbTooltipModule, TranslateModule]
})
export class ReceiptComponent implements OnInit, OnDestroy {
  private appConfigService = inject(AppConfigService);
  protected utilsService = inject(UtilsService);
  protected authenticationService = inject(AuthenticationService);
  protected appDataService = inject(AppDataService);

  /**
   * The access code handed over where the interface is embedded elsewhere:
   * on the page of the reporting person it is the one of the session, which
   * is consumed here so that it is kept nowhere else.
   */
  @Input() receipt = "";

  receiptId = "";
  embedded = false;

  public ngOnInit(): void {
    this.embedded = !!this.receipt;

    if (!this.embedded) {
      this.receipt = this.authenticationService.session.receipt;
      this.authenticationService.session.receipt = undefined;
    }

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
