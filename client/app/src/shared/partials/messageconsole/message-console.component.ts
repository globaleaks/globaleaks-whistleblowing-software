import {AfterViewChecked, ChangeDetectorRef, Component, ElementRef, inject} from "@angular/core";
import {LiveAnnouncer} from "@angular/cdk/a11y";
import {AppDataService} from "@app/app-data.service";
import {ErrorCodes} from "@app/models/app/error-code";

import {TranslatePipe} from "@ngx-translate/core";

@Component({
    selector: "src-message-console",
    templateUrl: "./message-console.component.html",
    standalone: true,
    imports: [TranslatePipe]
})
export class MessageConsoleComponent implements AfterViewChecked {
  private readonly cdr = inject(ChangeDetectorRef);
  private readonly element = inject(ElementRef);
  private readonly liveAnnouncer = inject(LiveAnnouncer);
  appDataService = inject(AppDataService);

  private timeoutId: any;
  private timeoutRunning = false;

  dismissError() {
    clearTimeout(this.timeoutId);
    this.timeoutRunning = false;
    this.appDataService.errorCodes = new ErrorCodes();
  }

  ngAfterViewChecked(): void {
    if (!this.timeoutRunning && this.appDataService.errorCodes.code !== -1) {
      this.timeoutRunning = true;
      // The error is read as soon as it is shown: it goes away by itself after a few seconds
      const text = (this.element.nativeElement as HTMLElement).textContent?.replace(/[\s×]+/g, " ").trim();
      if (text) {
        this.liveAnnouncer.announce(text, "assertive");
      }
      this.timeoutId = setTimeout(() => {
        this.dismissError();
        this.cdr.markForCheck();
      }, 3000);
    }
  }
}
