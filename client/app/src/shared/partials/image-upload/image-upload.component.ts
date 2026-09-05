import {RenderSchedulerService} from "@app/shared/services/render-scheduler.service";
import {AfterViewInit, Component, ElementRef, OnDestroy, OnInit, inject, viewChild} from "@angular/core";
import {FlowConfig, NgxFlowModule} from "@flowjs/ngx-flow";
import {HttpService} from "@app/shared/services/http.service";
import {Subscription} from "rxjs";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {FlowOptions} from "@flowjs/flow.js";
import {UtilsService} from "@app/shared/services/utils.service";
import {FormsModule} from "@angular/forms";
import {TranslateModule} from "@ngx-translate/core";
import {NgbTooltipModule} from '@ng-bootstrap/ng-bootstrap';


@Component({
    selector: "src-image-upload",
    templateUrl: "./image-upload.component.html",
    standalone: true,
    imports: [FormsModule, NgbTooltipModule, NgxFlowModule, TranslateModule]
})
export class ImageUploadComponent implements AfterViewInit, OnDestroy, OnInit {
  private readonly renderScheduler = inject(RenderSchedulerService);
  protected authenticationService = inject(AuthenticationService);
  private readonly httpService = inject(HttpService);
  private readonly utilsService = inject(UtilsService);

  readonly flow = viewChild.required<FlowConfig>("flowAdvanced");

  imageUploadModel: Record<string, any>;
  imageUploadModelAttr: string;
  imageUploadId: string;
  imageUploadObj: { files: [] } = {files: []};
  autoUploadSubscription: Subscription;
  filemodel: any;
  currentTimestamp = new Date().getTime();
  flowConfig: FlowOptions;
  readonly uploaderInput = viewChild.required<ElementRef<HTMLInputElement>>("uploader");

  ngOnInit() {
    this.filemodel = this.imageUploadModel[this.imageUploadModelAttr];
    this.flowConfig = this.utilsService.getFlowOptions({
      target: "api/admin/files/" + this.imageUploadId,
      singleFile: true
    });
  }

  ngAfterViewInit() {
    this.autoUploadSubscription = this.flow().events$.subscribe(event => {
      if (event.type === "filesSubmitted") {
        this.imageUploadModel[this.imageUploadModelAttr] = true;
        this.renderScheduler.schedule();
      }
    });
  }

  onFileSelected(files: FileList | null) {
    const file = files?.[0];
    if (file) {
      const fileNameParts = file.name.split(".");
      const fileExtension = fileNameParts.pop();
      const fileNameWithoutExtension = fileNameParts.join(".");
      const timestamp = new Date().getTime();
      const fileNameWithTimestamp = `${fileNameWithoutExtension}_${timestamp}.${fileExtension}`;
      const modifiedFile = new File([file], fileNameWithTimestamp, {type: file.type});
      const flowJsInstance = this.flow().flowJs;

      flowJsInstance.addFile(modifiedFile);
      flowJsInstance.upload();
      this.filemodel = modifiedFile;
      flowJsInstance.on('complete', () => {
        this.currentTimestamp = new Date().getTime();
        this.renderScheduler.schedule();
      });
    }
  }

  triggerFileInputClick() {
    this.uploaderInput().nativeElement.click();
  }

  ngOnDestroy() {
    this.autoUploadSubscription.unsubscribe();
  }

  deletePicture() {
    this.httpService.requestDeleteResource("api/admin/files/" + this.imageUploadId)
      .subscribe(() => {
        if (this.imageUploadModel) {
          this.imageUploadModel[this.imageUploadModelAttr] = "";
        }
        this.imageUploadObj.files = [];
        this.filemodel = ""
        this.uploaderInput().nativeElement.value = "";
      });
  }

  getCurrentTimestamp(): number {
    return this.currentTimestamp;
  }
}
