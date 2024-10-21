import {Component, Input, ViewChild, ElementRef, ChangeDetectorRef, EventEmitter, Output, inject} from "@angular/core";
import {UtilsService} from "@app/shared/services/utils.service";
import {AppDataService} from "@app/app-data.service";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import * as Flow from "@flowjs/flow.js";
import {RecieverTipData} from "@app/models/receiver/receiver-tip-data";
import {FlowFile} from "@flowjs/flow.js";
import {NgClass} from "@angular/common";
import {WbFilesComponent} from "../wbfiles/wb-files.component";
import {FormsModule} from "@angular/forms";
import {NgxFlowModule} from "@flowjs/ngx-flow";
import {TranslateModule} from "@ngx-translate/core";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {OrderByPipe} from "@app/shared/pipes/order-by.pipe";
import {FilterPipe} from "@app/shared/pipes/filter.pipe";
import {NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";

@Component({
    selector: "src-tip-upload-wbfile",
    templateUrl: "./tip-upload-wb-file.component.html",
    standalone: true,
    imports: [WbFilesComponent, FormsModule, NgbTooltipModule, NgClass, NgxFlowModule, TranslateModule, TranslatorPipe, OrderByPipe, FilterPipe]
})
export class TipUploadWbFileComponent {
  private cdr = inject(ChangeDetectorRef);
  private authenticationService = inject(AuthenticationService);
  protected utilsService = inject(UtilsService);
  protected appDataService = inject(AppDataService);

  @ViewChild('uploader') uploaderInput: ElementRef<HTMLInputElement>;
  @Input() tip: RecieverTipData;
  @Input() key: string;
  @Output() dataToParent = new EventEmitter<string>();
  collapsed = false;
  file_upload_description: string = "";
  fileInput: string = "fileinput";
  showError: boolean = false;
  errorFile: FlowFile | null;

  onFileSelected(files: FileList | null) {
    if (files && files.length > 0) {
      const file = files[0];
      const flowJsInstance = this.utilsService.flowDefault;

      flowJsInstance.opts.target = "api/recipient/rtips/" + this.tip.id + "/rfiles";
      flowJsInstance.opts.singleFile = true;
      flowJsInstance.opts.query = {description: this.file_upload_description, visibility: this.key, fileSizeLimit: this.appDataService.public.node.maximum_filesize * 1024 * 1024},
      flowJsInstance.opts.headers = {"X-Session": this.authenticationService.session.id};
      flowJsInstance.on("fileSuccess", (_) => {
        this.dataToParent.emit()
        this.errorFile = null;
      });
      flowJsInstance.on("fileError", (file, _) => {
        this.showError = true;
        this.errorFile = file;
        if (this.uploaderInput) {
          this.uploaderInput.nativeElement.value = "";
        }
        this.cdr.detectChanges();
      });

      this.utilsService.onFlowUpload(flowJsInstance, file);
    }
  }

  listenToWbfiles(files: string) {
    this.utilsService.deleteResource(this.tip.rfiles, files);
    this.dataToParent.emit()
  }

  protected dismissError() {
    this.showError = false;
  }
}
