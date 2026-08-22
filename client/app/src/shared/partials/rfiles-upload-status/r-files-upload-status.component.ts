import {Component, input} from "@angular/core";
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
  readonly uploading = input<boolean>();
  readonly progress = input<number | undefined>();
  readonly estimatedTime = input<number | undefined>();
  protected readonly isFinite = isFinite;

  protected getEstimatedTimeValue(): number | undefined {
    const estimatedTime = this.estimatedTime();
    if (!estimatedTime || !isFinite(estimatedTime)) {
      return estimatedTime;
    }

    if (estimatedTime >= 3600) {
      return Math.ceil(estimatedTime / 3600);
    }

    if (estimatedTime >= 60) {
      return Math.ceil(estimatedTime / 60);
    }

    return Math.ceil(estimatedTime);
  }

  protected getEstimatedTimeUnit(): string {
    const estimatedTime = this.estimatedTime();
    if (!estimatedTime || !isFinite(estimatedTime)) {
      return "seconds";
    }

    if (estimatedTime >= 3600) {
      return "hours";
    }

    if (estimatedTime >= 60) {
      return "minutes";
    }

    return "seconds";
  }
}
