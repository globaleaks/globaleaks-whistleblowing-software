import {Component, Input} from "@angular/core";
import { NgStyle } from "@angular/common";
import { TranslateModule } from "@ngx-translate/core";
import { TranslatorPipe } from "@app/shared/pipes/translate";

@Component({
    selector: "src-rfiles-upload-status",
    templateUrl: "./r-files-upload-status.component.html",
    standalone: true,
    imports: [NgStyle, TranslateModule, TranslatorPipe]
})
export class RFilesUploadStatusComponent {
  @Input() uploading: boolean | undefined;
  @Input() progress: number | undefined;
  @Input() estimatedTime: number | undefined;
  protected readonly isFinite = isFinite;
}
