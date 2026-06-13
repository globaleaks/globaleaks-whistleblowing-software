import {Component, Input} from "@angular/core";
import {NgStyle} from "@angular/common";
import {TranslateModule} from "@ngx-translate/core";
// import {TranslatorPipe} from "@app/shared/pipes/translate";

type EstimatedTime = {
  value: number;
  unit: "seconds" | "minutes" | "hours" | "days";
};

@Component({
    selector: "src-rfiles-upload-status",
    templateUrl: "./r-files-upload-status.component.html",
    standalone: true,
    imports: [NgStyle, TranslateModule/*, TranslatorPipe*/]
})

export class RFilesUploadStatusComponent {
  @Input() uploading: boolean | undefined;
  @Input() progress: number | undefined;
  @Input() estimatedTime: number | undefined;

  protected readonly isFinite = isFinite;

  getFormattedTime(totalSeconds: number | undefined): EstimatedTime | null {
    if (totalSeconds === undefined || !Number.isFinite(totalSeconds) || totalSeconds < 0) {
      return null;
    }
    
    if (totalSeconds >= 86400) {
      return { value: Math.floor(totalSeconds / 86400), unit: 'days'};
    }

    if (totalSeconds >= 3600) {
      return { value: Math.floor(totalSeconds / 3600), unit: 'hours'};
    }

    if (totalSeconds >= 60) {
      return { value: Math.floor(totalSeconds / 60), unit: 'minutes'};
    }

    return { value: Math.floor(totalSeconds), unit: "seconds"};
  }
}
