import {Component, EventEmitter, Input, OnInit, Output, inject} from "@angular/core";
import {AppDataService} from "@app/app-data.service";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {HttpService} from "@app/shared/services/http.service";
import {CryptoService} from "@app/shared/services/crypto.service";
import {MaskService} from "@app/shared/services/mask.service";
import {PreferenceResolver} from "@app/shared/resolvers/preference.resolver";
import {ReceiverTipService} from "@app/services/helper/receiver-tip.service";
import {RedactionData} from "@app/models/component-model/redaction";
import {RFile} from "@app/models/app/shared-public-model";
import {ReceiversById} from "@app/models/receiver/receiver-tip-data";
import {DatePipe} from "@angular/common";
import {NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {TranslateModule} from "@ngx-translate/core";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {ByteFmtPipe} from "@app/shared/pipes/byte-fmt.pipe";

@Component({
    selector: "src-wbfiles",
    templateUrl: "./wb-files.component.html",
    standalone: true,
    imports: [DatePipe, NgbTooltipModule, TranslateModule, TranslatorPipe, ByteFmtPipe]
})
export class WbFilesComponent implements OnInit {
  private appDataService = inject(AppDataService);
  private cryptoService = inject(CryptoService);
  private httpService = inject(HttpService);
  protected authenticationService = inject(AuthenticationService);
  protected maskService = inject(MaskService);
  protected preferenceResolver = inject(PreferenceResolver);
  protected tipService = inject(ReceiverTipService);

  @Input() wbFile: RFile;
  @Input() ctx: string;
  @Input() redactMode = false;
  @Input() receivers_by_id: ReceiversById;
  @Output() updated = new EventEmitter<any>();

  ngOnInit(): void {
  }

  isMasked(): boolean {
    return !!this.wbFile.masked;
  }

  displayName(): string {
    // Privileged recipients receive the real name from the server; cover it
    // with the same placeholder used elsewhere while outside the masking editor.
    if (this.isMasked() && !this.redactMode &&
        (this.preferenceResolver.dataModel?.can_mask_information ||
         this.preferenceResolver.dataModel?.can_redact_information)) {
      return String.fromCharCode(0x2591).repeat(this.wbFile.name.length);
    }

    return this.wbFile.name;
  }

  redactFileOperation(operation: string) {
    const redactionData: RedactionData = {
      reference_id: this.wbFile.id,
      internaltip_id: this.tipService.tip.id,
      entry: "0",
      operation: operation,
      content_type: "file",
      temporary_redaction: [],
      permanent_redaction: [],
    };

    if (operation === "full-mask") {
      redactionData.temporary_redaction = [{start: "-inf", end: "inf"}];
    }

    const redaction = this.maskService.getRedaction(this.wbFile.id, "0", this.tipService.tip);

    if (redaction) {
      redactionData.id = redaction.id;
      this.tipService.updateRedaction(redactionData, this.tipService.tip.id);
    } else {
      this.tipService.newRedaction(redactionData, this.tipService.tip.id);
    }
  }

  downloadWBFile(wbFile: RFile) {

    const param = JSON.stringify({});
    this.httpService.requestToken(param).subscribe
    (
      {
        next: async token => {
          this.cryptoService.proofOfWork(token).subscribe(
            (ans) => {
              if (this.authenticationService.session?.role === "receiver") {
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
