import {AfterViewChecked, Component, inject} from "@angular/core";
import {AppDataService} from "@app/app-data.service";
import {ErrorCodes} from "@app/models/app/error-code";

import {TranslateModule} from "@ngx-translate/core";
import {TranslatorPipe} from "@app/shared/pipes/translate";

@Component({
    selector: "messageconsole",
    templateUrl: "./message-console.component.html",
    standalone: true,
    imports: [TranslateModule, TranslatorPipe]
})
export class MessageConsoleComponent implements AfterViewChecked {
  appDataService = inject(AppDataService);

  private timeoutId: any;
  private timeoutRunning: boolean = false;

  dismissError() {
    clearTimeout(this.timeoutId);
    this.timeoutRunning = false;
    this.appDataService.errorCodes = new ErrorCodes();
  }

  ngAfterViewChecked(): void {
    if (!this.timeoutRunning && this.appDataService.errorCodes.code !== -1) {
      this.timeoutRunning = true;
      this.timeoutId = setTimeout(() => {
        this.dismissError();
      }, 3000);
    }
  }
}
