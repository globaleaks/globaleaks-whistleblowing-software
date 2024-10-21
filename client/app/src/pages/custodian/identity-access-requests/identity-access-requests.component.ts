import { Component, inject } from "@angular/core";
import {IarResolver} from "@app/shared/resolvers/iar-resolver.service";
import {UtilsService} from "@app/shared/services/utils.service";
import {HttpService} from "@app/shared/services/http.service";
import {NgbModal} from "@ng-bootstrap/ng-bootstrap";
import {
  TipOperationFileIdentityAccessReplyComponent
} from "@app/shared/modals/tip-operation-file-identity-access-reply/tip-operation-file-identity-access-reply.component";
import { DatePipe } from "@angular/common";
import { TranslateModule } from "@ngx-translate/core";
import { TranslatorPipe } from "@app/shared/pipes/translate";

@Component({
    selector: "src-identity-access-requests",
    templateUrl: "./identity-access-requests.component.html",
    standalone: true,
    imports: [DatePipe, TranslateModule, TranslatorPipe]
})
export class IdentityAccessRequestsComponent {
  private modalService = inject(NgbModal);
  private httpService = inject(HttpService);
  protected iarResolver = inject(IarResolver);
  protected utilsService = inject(UtilsService);


  authorizeIdentityAccessRequest(iar_id: string) {
    this.httpService.authorizeIdentity("api/custodian/iars/" + iar_id, {
      "reply": "authorized",
      "reply_motivation": ""
    }).subscribe(
      {
        next: () => {
          this.reload();
        }
      }
    );
  }

  reload() {
    this.iarResolver.reload();
  }

  fileDeniedIdentityAccessReply(iar_id: string) {
    const modalRef = this.modalService.open(TipOperationFileIdentityAccessReplyComponent, {
      backdrop: 'static',
      keyboard: false
    });
    modalRef.componentInstance.iar_id = iar_id;
    modalRef.componentInstance.confirmFunction = () => {
      this.reload();
    };

  }
}
