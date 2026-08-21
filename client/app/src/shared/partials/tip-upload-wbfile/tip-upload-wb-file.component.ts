import {CollapsiblePanelComponent} from "@app/shared/components/collapsible-panel/collapsible-panel.component";
import {Component, ElementRef, ChangeDetectorRef, inject, input, viewChild, output} from "@angular/core";
import {UtilsService} from "@app/shared/services/utils.service";
import {AppDataService} from "@app/app-data.service";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {ReceiverTipService} from "@app/services/helper/receiver-tip.service";
import {RecieverTipData} from "@app/models/receiver/receiver-tip-data";
import {FlowFile} from "@flowjs/flow.js";
import {WbFilesComponent} from "../wbfiles/wb-files.component";
import {FormsModule} from "@angular/forms";
import {NgxFlowModule} from "@flowjs/ngx-flow";
import {TranslateModule} from "@ngx-translate/core";
import {OrderByPipe} from "@app/shared/pipes/order-by.pipe";
import {FilterPipe} from "@app/shared/pipes/filter.pipe";
import {NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";

@Component({
    selector: "src-tip-upload-wbfile",
    templateUrl: "./tip-upload-wb-file.component.html",
    standalone: true,
    imports: [CollapsiblePanelComponent, WbFilesComponent, FormsModule, NgbTooltipModule, NgxFlowModule, TranslateModule, OrderByPipe, FilterPipe]
})
export class TipUploadWbFileComponent {
  private cdr = inject(ChangeDetectorRef);
  private authenticationService = inject(AuthenticationService);
  protected utilsService = inject(UtilsService);
  protected appDataService = inject(AppDataService);
  protected tipService = inject(ReceiverTipService);

  readonly uploaderInput = viewChild<ElementRef<HTMLInputElement>>('uploader');
  readonly tip = input.required<RecieverTipData>();
  readonly key = input<string>();
  readonly redactMode = input(false);
  readonly updated = output<void>();
  collapsed = false;
  file_upload_description = "";
  fileInput = "fileinput";
  showError = false;
  errorFile: FlowFile | null;

  onFileSelected(files: FileList | null) {
    if (files && files.length > 0) {
      const file = files[0];
      const flowJsInstance = this.utilsService.getFlowInstance({
        target: "api/recipient/rtips/" + this.tip().id + "/rfiles",
        singleFile: true,
        query: {description: this.file_upload_description, visibility: this.key(), fileSizeLimit: this.appDataService.public.node.maximum_filesize * 1024 * 1024}
      });
      flowJsInstance.on("fileSuccess", () => {
        this.updated.emit()
        this.errorFile = null;
        this.cdr.detectChanges();
      });
      flowJsInstance.on("fileError", (file) => {
        this.showError = true;
        this.errorFile = file;
        const uploaderInput = this.uploaderInput();
        if (uploaderInput) {
          uploaderInput.nativeElement.value = "";
        }
        this.cdr.detectChanges();
      });

      this.utilsService.onFlowUpload(flowJsInstance, file);
    }
  }

  listenToWbfiles(id: string) {
    this.utilsService.deleteResource(this.tip().rfiles, id);
    this.updated.emit();
  }

  protected dismissError() {
    this.showError = false;
  }
}
