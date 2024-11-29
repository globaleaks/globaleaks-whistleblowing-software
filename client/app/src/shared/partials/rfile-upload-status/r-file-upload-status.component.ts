import {Component, EventEmitter, Input, Output, inject} from "@angular/core";
import {UtilsService} from "@app/shared/services/utils.service";
import {AppDataService} from "@app/app-data.service";
import {Transfer} from "@flowjs/ngx-flow";
import {NgClass, NgStyle} from "@angular/common";
import {TranslateModule} from "@ngx-translate/core";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {ByteFmtPipe} from "@app/shared/pipes/byte-fmt.pipe";

@Component({
    selector: "src-rfile-upload-status",
    templateUrl: "./r-file-upload-status.component.html",
    standalone: true,
    imports: [NgClass, NgStyle, TranslateModule, TranslatorPipe, ByteFmtPipe]
})
export class RFileUploadStatusComponent {
  protected utilsService = inject(UtilsService);
  protected appDataService = inject(AppDataService);
  @Output() dataToParent: EventEmitter<any> = new EventEmitter<any>();
  @Input() file: Transfer;
  @Input() formUploader: boolean;
}
