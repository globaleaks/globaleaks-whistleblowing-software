import {Component, inject} from "@angular/core";
import {IarResolver} from "@app/shared/resolvers/iar-resolver.service";
import {UtilsService} from "@app/shared/services/utils.service";
import {HttpService} from "@app/shared/services/http.service";
import {NgbModal, NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {
  TipOperationFileIdentityAccessReplyComponent
} from "@app/shared/modals/tip-operation-file-identity-access-reply/tip-operation-file-identity-access-reply.component";
import {DatePipe} from "@angular/common";
import {TranslateModule} from "@ngx-translate/core";

@Component({
    selector: "src-identity-access-requests",
    templateUrl: "./identity-access-requests.component.html",
    standalone: true,
    imports: [DatePipe, NgbTooltipModule, TranslateModule]
})
export class IdentityAccessRequestsComponent {
  private modalService = inject(NgbModal);
  private httpService = inject(HttpService);
  protected iarResolver = inject(IarResolver);
  protected utilsService = inject(UtilsService);

  usersNames: Record<string, string> = {};

  constructor() {
    this.utilsService.runUserOperation("get_users_names", {}, false).subscribe({
      next: response => {
        this.usersNames = response as Record<string, string>;
      }
    });
  }

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
