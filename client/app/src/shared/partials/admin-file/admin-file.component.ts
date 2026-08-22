import {Component, ElementRef, inject, input, viewChild} from "@angular/core";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {UtilsService} from "@app/shared/services/utils.service";
import {AppConfigService} from "@app/services/root/app-config.service";
import {AppDataService} from "@app/app-data.service";
import {AdminFile} from "@app/models/component-model/admin-file";
import {NgClass} from "@angular/common";
import {NgxFlowModule} from "@flowjs/ngx-flow";
import {TranslateModule} from "@ngx-translate/core";
import {TranslatorPipe} from "@app/shared/pipes/translate";

@Component({
    selector: "src-admin-file",
    templateUrl: "./admin-file.component.html",
    standalone: true,
    imports: [NgClass, NgxFlowModule, TranslateModule, TranslatorPipe]
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
    if (files && files.length > 0) {
      const file = files[0];
      const flowJsInstance = this.utilsService.getFlowInstance({
        target: "api/admin/files/" + filetype,
        singleFile: true,
        query: {fileSizeLimit: this.node.dataModel.maximum_filesize * 1024 * 1024}
      });

      flowJsInstance.on("fileSuccess", (_) => {
        this.appConfigService.reinit(false);
	const callback = this.callback();
 if (callback) {
          callback();
	}
      });
      flowJsInstance.on("fileError", (_) => {
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
        this.appConfigService.reinit(false);
	const callback = this.callback();
 if (callback) {
          callback();
	}
      }
    );
  }
}
