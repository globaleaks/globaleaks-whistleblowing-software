import {Component, ElementRef, Input, ViewChild, inject} from "@angular/core";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {UtilsService} from "@app/shared/services/utils.service";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import Flow from "@flowjs/flow.js";
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
  protected authenticationService = inject(AuthenticationService);

  @Input() adminFile: AdminFile;
  @Input() present: boolean;
  @Input() callback!: () => void;
  @ViewChild("uploader") uploaderInput!: ElementRef<HTMLInputElement>;

  onFileSelected(files: FileList | null, filetype: string) {
    if (files && files.length > 0) {
      const file = files[0];
      const flowJsInstance = new Flow({
        target: "api/admin/files/" + filetype,
        singleFile: true,
        allowDuplicateUploads: false,
        testChunks: false,
        permanentErrors: [500, 501],
        generateUniqueIdentifier: () => {
          return crypto.randomUUID();
        },
        query: {fileSizeLimit: this.node.dataModel.maximum_filesize * 1024 * 1024},
        headers: {"X-Session": this.authenticationService.session.id}
      });

      flowJsInstance.on("fileSuccess", (_) => {
        this.appConfigService.reinit(false);
	if (this.callback) {
          this.callback();
	}
      });
      flowJsInstance.on("fileError", (_) => {
        if (this.uploaderInput) {
          this.uploaderInput.nativeElement.value = "";
        }
      });
      this.utilsService.onFlowUpload(flowJsInstance, file)
    }
  }

  deleteFile(url: string): void {
    this.utilsService.deleteFile(url).subscribe(
      () => {
        this.appConfigService.reinit(false);
	if (this.callback) {
          this.callback();
	}
      }
    );
  }
}
