import {Component, inject, ChangeDetectionStrategy} from "@angular/core";
import {NgbActiveModal} from "@ng-bootstrap/ng-bootstrap";
import {UtilsService} from "@app/shared/services/utils.service";
import {HttpService} from "@app/shared/services/http.service";
import {Router} from "@angular/router";
import {TranslateModule} from "@ngx-translate/core";


@Component({
    changeDetection: ChangeDetectionStrategy.OnPush,
    selector: "src-delete-confirmation",
    templateUrl: "./delete-confirmation.component.html",
    standalone: true,
    imports: [TranslateModule]
})
export class DeleteConfirmationComponent {
  private modalService = inject(NgbActiveModal);
  private httpService = inject(HttpService);
  private utils = inject(UtilsService);
  private router = inject(Router);


  args: any;
  selected_tips: string[];
  operation: string;
  confirmFunction: () => void;

  confirm() {
    this.cancel();
    this.confirmFunction();
    const args = this.args;
    if (args) {
      if (args.operation === "delete") {
        return this.httpService.requestDeleteReceiverTip(args.tip.id)
          .subscribe(() => {
            this.router.navigate(["/recipient/reports"]).then();
          });
      }
      return;
    }
    const operation = this.operation;
    if (operation) {
      if (["delete"].indexOf(operation) === -1) {
        return;
      }
    }

    const selected_tips = this.selected_tips;
    if (selected_tips) {
      return this.utils.runRecipientOperation(operation, {"rtips": selected_tips}, true).subscribe({
        next: () => {
          this.utils.reloadCurrentRoute();
        }
      });
    } else {
      return null;
    }

  }

  cancel() {
    this.modalService.dismiss();
  }

}
