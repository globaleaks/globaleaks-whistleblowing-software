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

  protected getEstimatedTimeValue(): number | undefined {
    if (!this.estimatedTime || !isFinite(this.estimatedTime)) {
      return this.estimatedTime;
    }

    if (this.estimatedTime >= 3600) {
      return Math.ceil(this.estimatedTime / 3600);
    }

    if (this.estimatedTime >= 60) {
      return Math.ceil(this.estimatedTime / 60);
    }

    return Math.ceil(this.estimatedTime);
  }

  protected getEstimatedTimeUnit(): string {
    if (!this.estimatedTime || !isFinite(this.estimatedTime)) {
      return "seconds";
    }

    if (this.estimatedTime >= 3600) {
      return "hours";
    }

    if (this.estimatedTime >= 60) {
      return "minutes";
    }

    return "seconds";
  }
}
