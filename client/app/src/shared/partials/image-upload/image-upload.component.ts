import {HttpClient} from "@angular/common/http";
import {AfterViewInit, Component, ElementRef, Input, OnDestroy, OnInit, ViewChild, inject} from "@angular/core";
import {FlowDirective, NgxFlowModule} from "@flowjs/ngx-flow";
import {Subscription} from "rxjs";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {FlowOptions} from "@flowjs/flow.js";
import {UtilsService} from "@app/shared/services/utils.service";
import {FormsModule} from "@angular/forms";
import {NgOptimizedImage} from "@angular/common";
import {TranslateModule} from "@ngx-translate/core";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {NgbTooltipModule} from '@ng-bootstrap/ng-bootstrap';


@Component({
    selector: "src-image-upload",
    templateUrl: "./image-upload.component.html",
    standalone: true,
    imports: [FormsModule, NgbTooltipModule, NgxFlowModule, NgOptimizedImage, TranslateModule, TranslatorPipe]
})
export class ImageUploadComponent implements AfterViewInit, OnDestroy, OnInit {
  private http = inject(HttpClient);
  protected authenticationService = inject(AuthenticationService);
  private utilsService = inject(UtilsService);

  @ViewChild("flowAdvanced")
  flow: FlowDirective;
  @ViewChild("uploader") uploaderElementRef!: ElementRef<HTMLInputElement>;

  @Input() imageUploadModel: { [key: string]: any };
  @Input() imageUploadModelAttr: string;
  @Input() imageUploadId: string;
  imageUploadObj: { files: [] } = {files: []};
  autoUploadSubscription: Subscription;
  filemodel: any;
  currentTImestamp = new Date().getTime();
  flowConfig: FlowOptions;
  @ViewChild('uploader') uploaderInput: ElementRef<HTMLInputElement>;

  ngOnInit() {
    this.filemodel = this.imageUploadModel[this.imageUploadModelAttr];
    this.flowConfig = this.utilsService.flowDefault.opts;
    this.flowConfig.target = "api/admin/files/"+this.imageUploadId;
    this.flowConfig.singleFile = true;
    this.flowConfig.headers = {"X-Session": this.authenticationService.session.id};
  }

  ngAfterViewInit() {
    this.autoUploadSubscription = this.flow.events$.subscribe(event => {
      if (event.type === "filesSubmitted") {
        this.imageUploadModel[this.imageUploadModelAttr] = true;
      }
    });
  }

  onFileSelected(files: FileList | null) {
    if (files && files.length > 0) {
      const file = files[0];
      const fileNameParts = file.name.split(".");
      const fileExtension = fileNameParts.pop();
      const fileNameWithoutExtension = fileNameParts.join(".");
      const timestamp = new Date().getTime();
      const fileNameWithTimestamp = `${fileNameWithoutExtension}_${timestamp}.${fileExtension}`;
      const modifiedFile = new File([file], fileNameWithTimestamp, {type: file.type});
      const flowJsInstance = this.flow.flowJs;

      flowJsInstance.addFile(modifiedFile);
      flowJsInstance.upload();
      this.currentTImestamp = new Date().getTime();
      this.filemodel = modifiedFile;
    }
  }

  triggerFileInputClick() {
    this.uploaderElementRef.nativeElement.click();
  }

  ngOnDestroy() {
    this.autoUploadSubscription.unsubscribe();
  }

  deletePicture() {
    this.http
      .delete("api/admin/files/" + this.imageUploadId)
      .subscribe(() => {
        if (this.imageUploadModel) {
          this.imageUploadModel[this.imageUploadModelAttr] = "";
        }
        this.imageUploadObj.files = [];
        this.filemodel = ""
        if (this.uploaderInput) {
          this.uploaderInput.nativeElement.value = "";
        }
      });
  }

  getCurrentTimestamp(): number {
    return this.currentTImestamp;
  }

}
