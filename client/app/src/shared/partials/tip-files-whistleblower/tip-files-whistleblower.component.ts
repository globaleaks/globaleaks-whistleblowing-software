import { Component, Input, inject } from "@angular/core";
import {UtilsService} from "@app/shared/services/utils.service";
import {WbtipService} from "@app/services/helper/wbtip.service";
import {HttpService} from "@app/shared/services/http.service";
import {AppDataService} from "@app/app-data.service";
import {CryptoService} from "@app/shared/services/crypto.service";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {WbFile} from "@app/models/app/shared-public-model";
import { DatePipe } from "@angular/common";
import { RFileUploadButtonComponent } from "../rfile-upload-button/r-file-upload-button.component";
import { TranslateModule } from "@ngx-translate/core";
import { TranslatorPipe } from "@app/shared/pipes/translate";
import { ByteFmtPipe } from "@app/shared/pipes/byte-fmt.pipe";
import { OrderByPipe } from "@app/shared/pipes/order-by.pipe";


@Component({
    selector: "src-tip-files-whistleblower",
    templateUrl: "./tip-files-whistleblower.component.html",
    standalone: true,
    imports: [RFileUploadButtonComponent, DatePipe, TranslateModule, TranslatorPipe, ByteFmtPipe, OrderByPipe]
})
export class TipFilesWhistleblowerComponent {
  private appDataService = inject(AppDataService);
  private cryptoService = inject(CryptoService);
  private httpService = inject(HttpService);
  protected authenticationService = inject(AuthenticationService);
  protected utilsService = inject(UtilsService);
  protected wbTipService = inject(WbtipService);

  @Input() fileUploadUrl: string;
  collapsed = false;

  downloadWBFile(wbFile: WbFile) {

    const param = JSON.stringify({});
    this.httpService.requestToken(param).subscribe
    (
      {
        next: async token => {
          this.cryptoService.proofOfWork(token.id).subscribe(
              (ans) => {
                window.open("api/whistleblower/wbtip/wbfiles/" + wbFile.id + "?token=" + token.id + ":" + ans);
                this.appDataService.updateShowLoadingPanel(false);
              }
          );
        }
      }
    );
  }

  getSortedWBFiles(data: WbFile[]): WbFile[] {
    return data;
  }

  public toggleColLapse() {
    this.collapsed = !this.collapsed;
  }
}
