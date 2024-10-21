import { Component, EventEmitter, Input, OnInit, Output, inject } from "@angular/core";
import {AppDataService} from "@app/app-data.service";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {HttpService} from "@app/shared/services/http.service";
import {CryptoService} from "@app/shared/services/crypto.service";
import {RFile} from "@app/models/app/shared-public-model";
import {ReceiversById} from "@app/models/reciever/reciever-tip-data";
import { DatePipe } from "@angular/common";
import { TranslateModule } from "@ngx-translate/core";
import { TranslatorPipe } from "@app/shared/pipes/translate";
import { ByteFmtPipe } from "@app/shared/pipes/byte-fmt.pipe";

@Component({
    selector: "src-wbfiles",
    templateUrl: "./wb-files.component.html",
    standalone: true,
    imports: [DatePipe, TranslateModule, TranslatorPipe, ByteFmtPipe]
})
export class WbFilesComponent implements OnInit {
  private appDataService = inject(AppDataService);
  private cryptoService = inject(CryptoService);
  private httpService = inject(HttpService);
  protected authenticationService = inject(AuthenticationService);

  @Input() wbFile: RFile;
  @Input() ctx: string;
  @Input() receivers_by_id: ReceiversById;
  @Output() dataToParent = new EventEmitter<any>();

  ngOnInit(): void {
  }

  deleteWBFile(wbFile: RFile) {
    if (this.authenticationService.session.role === "receiver") {
      this.httpService.deleteDBFile(wbFile.id).subscribe
      (
        {
          next: async _ => {
            this.dataToParent.emit(wbFile)
          }
        }
      );
    }
  }

  downloadWBFile(wbFile: RFile) {

    const param = JSON.stringify({});
    this.httpService.requestToken(param).subscribe
    (
      {
        next: async token => {
          this.cryptoService.proofOfWork(token.id).subscribe(
            (ans) => {
              if (this.authenticationService.session.role === "receiver") {
                window.open("api/recipient/rfiles/" + wbFile.id + "?token=" + token.id + ":" + ans);
              } else {
                window.open("api/whistleblower/wbtip/rfiles/" + wbFile.id + "?token=" + token.id + ":" + ans);
              }
              this.appDataService.updateShowLoadingPanel(false);
            }
          );
        }
      }
    );
  }
}
