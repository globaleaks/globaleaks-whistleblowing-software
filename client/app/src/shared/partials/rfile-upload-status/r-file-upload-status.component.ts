import {Component, inject, input, output} from "@angular/core";
import {UtilsService} from "@app/shared/services/utils.service";
import {AppDataService} from "@app/app-data.service";
import {Transfer} from "@flowjs/ngx-flow";
import {TranslateModule} from "@ngx-translate/core";
import {ByteFmtPipe} from "@app/shared/pipes/byte-fmt.pipe";

@Component({
    selector: "src-rfile-upload-status",
    templateUrl: "./r-file-upload-status.component.html",
    standalone: true,
    imports: [TranslateModule, ByteFmtPipe]
})
export class RFileUploadStatusComponent {
  protected utilsService = inject(UtilsService);
  protected appDataService = inject(AppDataService);
  readonly updated = output<string | null>();
  readonly file = input.required<Transfer>();
  readonly formUploader = input<boolean>();
}
