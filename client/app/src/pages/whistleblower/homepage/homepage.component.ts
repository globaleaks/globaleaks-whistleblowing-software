import {Component, inject, OnInit} from "@angular/core";
import {AppDataService} from "@app/app-data.service";
import {AppConfigService} from "@app/services/root/app-config.service";
import {Router} from "@angular/router";

import {MarkdownComponent} from "ngx-markdown";
import {ReceiptComponent} from "@app/shared/partials/receipt/receipt.component";
import {TranslateModule} from "@ngx-translate/core";
import {StripHtmlPipe} from "@app/shared/pipes/strip-html.pipe";

@Component({
    selector: "src-homepage",
    templateUrl: "./homepage.component.html",
    standalone: true,
    imports: [MarkdownComponent, ReceiptComponent, TranslateModule, StripHtmlPipe]
})
export class HomepageComponent  implements OnInit {
  protected appConfigService = inject(AppConfigService);
  protected appDataService = inject(AppDataService);
  private readonly router = inject(Router);

  ngOnInit(): void {
    if (this.appDataService.public.node.homepage === '/submission') {
      this.appConfigService.setPage("submissionpage");
    }
  }

  // The disclaimer is presented by the page of the submission itself, so that
  // it is shown as well to whoever reaches it without passing from here
  openSubmission() {
    if (this.appDataService.public.node.whistleblowing_destination === "/login") {
      void this.router.navigate(["/login"]);
      return this.appDataService.page;
    }

    this.appConfigService.setPage("submissionpage");
    return this.appDataService.page;
  }
}
