import {Component, Input} from "@angular/core";
import {NgStyle} from "@angular/common";
import {TranslateModule} from "@ngx-translate/core";
import {TranslatorPipe} from "@app/shared/pipes/translate";

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

  getFormattedTime(totalSeconds: number | undefined) {
    if (totalSeconds === undefined || !Number.isFinite(totalSeconds)) {
      return null;
    }
    const days = Math.floor(totalSeconds / 86400);
    const hours = Math.floor((totalSeconds % 86400) / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = Math.floor(totalSeconds % 60);

    return { days, hours, minutes, seconds};
  }
}
