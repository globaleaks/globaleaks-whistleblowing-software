import {Component, ElementRef, inject, input, viewChild, ChangeDetectionStrategy} from "@angular/core";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {UtilsService} from "@app/shared/services/utils.service";
import {AppConfigService} from "@app/services/root/app-config.service";
import {AppDataService} from "@app/app-data.service";
import {AdminFile} from "@app/models/component-model/admin-file";
import {NgxFlowModule} from "@flowjs/ngx-flow";
import {TranslateModule} from "@ngx-translate/core";

@Component({
    changeDetection: ChangeDetectionStrategy.OnPush,
    selector: "src-admin-file",
    templateUrl: "./admin-file.component.html",
    standalone: true,
    imports: [NgxFlowModule, TranslateModule]
})
export class AdminFileComponent {
  protected node = inject(NodeResolver);
  protected appConfigService = inject(AppConfigService);
  protected appDataService = inject(AppDataService);
  protected utilsService = inject(UtilsService);

  readonly adminFile = input.required<AdminFile>();
  readonly present = input<boolean>();
  readonly callback = input.required<() => void>();
  readonly uploaderInput = viewChild.required<ElementRef<HTMLInputElement>>("uploader");

  onFileSelected(files: FileList | null, filetype: string) {
    const file = files?.[0];
    if (file) {
      const flowJsInstance = this.utilsService.getFlowInstance({
        target: "api/admin/files/" + filetype,
        singleFile: true,
        query: {fileSizeLimit: this.node.dataModel.maximum_filesize * 1024 * 1024}
      });

      flowJsInstance.on("fileSuccess", () => {
        this.appConfigService.reinit();
	const callback = this.callback();
 if (callback) {
          callback();
	}
      });
      flowJsInstance.on("fileError", () => {
        const uploaderInput = this.uploaderInput();
        if (uploaderInput) {
          uploaderInput.nativeElement.value = "";
        }
      });
      this.utilsService.onFlowUpload(flowJsInstance, file)
    }
  }

  deleteFile(url: string): void {
    this.utilsService.deleteFile(url).subscribe(
      () => {
        this.appConfigService.reinit();
	const callback = this.callback();
 if (callback) {
          callback();
	}
      }
    );
  }
}
