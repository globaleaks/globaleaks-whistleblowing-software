import {Component, inject} from "@angular/core";
import {AppDataService} from "@app/app-data.service";
import {NgbModal} from "@ng-bootstrap/ng-bootstrap";
import {DisclaimerComponent} from "@app/shared/modals/disclaimer/disclaimer.component";
import {Observable} from "rxjs";
import {AppConfigService} from "@app/services/root/app-config.service";

import {MarkdownComponent} from "ngx-markdown";
import {ReceiptComponent} from "@app/shared/partials/receipt/receipt.component";
import {TranslateModule} from "@ngx-translate/core";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {StripHtmlPipe} from "@app/shared/pipes/strip-html.pipe";

@Component({
    selector: "src-homepage",
    templateUrl: "./homepage.component.html",
    standalone: true,
    imports: [MarkdownComponent, ReceiptComponent, TranslateModule, TranslatorPipe, StripHtmlPipe]
})
export class HomepageComponent {
  protected appConfigService = inject(AppConfigService);
  protected appDataService = inject(AppDataService);
  private modalService = inject(NgbModal);


  openSubmission() {
    if (this.appDataService.public.node.disclaimer_text) {
      return this.openDisclaimerModal().subscribe();
    }
    this.appConfigService.setPage("submissionpage");
    return this.appDataService.page;
  }

  openDisclaimerModal(): Observable<string> {
    return new Observable((observer) => {
      const modalRef = this.modalService.open(DisclaimerComponent, {backdrop: 'static', keyboard: false});
      modalRef.componentInstance.confirmFunction = () => {
        observer.complete()
        this.appConfigService.setPage("submissionpage");
        return this.appDataService.page;
      };
    });
  }
}
