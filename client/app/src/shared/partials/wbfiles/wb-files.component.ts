import {Component, EventEmitter, Input, Output} from "@angular/core";
import {AppDataService} from "@app/app-data.service";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {HttpService} from "@app/shared/services/http.service";
import {CryptoService} from "@app/shared/services/crypto.service";
import {RFile} from "@app/models/app/shared-public-model";
import {ReceiversById} from "@app/models/reciever/reciever-tip-data";
import { PreferenceResolver } from "@app/shared/resolvers/preference.resolver";
import { NgbModal } from "@ng-bootstrap/ng-bootstrap";
import { DownloadConfirmationComponent } from "@app/shared/modals/download-confirmation/download-confirmation.component";

@Component({
  selector: "src-wbfiles",
  templateUrl: "./wb-files.component.html"
})
export class WbFilesComponent {
  @Input() wbFile: RFile;
  @Input() ctx: string;
  @Input() canDelete: boolean = true;
  @Input() receivers_by_id: ReceiversById;
  @Output() dataToParent = new EventEmitter<any>();

  constructor(protected appDataService: AppDataService, private cryptoService: CryptoService, private httpService: HttpService, protected authenticationService: AuthenticationService, protected preferenceResolver:PreferenceResolver, private modalService: NgbModal) {
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

  showModalDownload(wbFile: RFile) {

    const modalRef = this.modalService.open(DownloadConfirmationComponent, {backdrop: 'static', keyboard: false});
    modalRef.componentInstance.arg = JSON.stringify({});
    modalRef.componentInstance.text = wbFile.status==="PENDING" ? "The selected file is not verified. Proceed anyway with the download?" : "The selected file is infected. Proceed anyway with the download?" ;
    modalRef.componentInstance.confirmFunction = (arg: string) => {
      this.httpService.requestToken(arg).subscribe
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
    )
    };
    return modalRef.result;

  }


  downloadWBFile(wbFile: RFile){

    const arg = JSON.stringify({});

    this.httpService.requestToken(arg).subscribe
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
  };



}
