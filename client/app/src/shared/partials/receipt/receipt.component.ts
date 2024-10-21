import {Component, inject} from "@angular/core";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {AppDataService} from "@app/app-data.service";
import {UtilsService} from "@app/shared/services/utils.service";
import {FormsModule} from "@angular/forms";
import {ReceiptValidatorDirective} from "../../directive/receipt-validator.directive";

import {TranslateModule} from "@ngx-translate/core";
import {TranslatorPipe} from "@app/shared/pipes/translate";

@Component({
    selector: "src-receipt",
    templateUrl: "./receipt.component.html",
    standalone: true,
    imports: [FormsModule, ReceiptValidatorDirective, TranslateModule, TranslatorPipe]
})
export class ReceiptComponent{
  protected utilsService = inject(UtilsService);
  protected authenticationService = inject(AuthenticationService);
  protected appDataService = inject(AppDataService);

  formattedReceipt = "";

  viewReport() {
    this.authenticationService.login(0, 'whistleblower', this.formattedReceipt);
    this.formattedReceipt = ""
  }
}
