import {AfterViewInit, ChangeDetectorRef, Component, EventEmitter, Input, OnDestroy, OnInit, Output, ViewChild, inject} from "@angular/core";
import {FlowDirective, Transfer, NgxFlowModule} from "@flowjs/ngx-flow";
import {AppDataService} from "@app/app-data.service";
import {ControlContainer, FormsModule, NgForm} from "@angular/forms";
import {Subscription} from "rxjs";
import {FlowOptions} from "@flowjs/flow.js";
import {Field} from "@app/models/resolvers/field-template-model";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {UtilsService} from "@app/shared/services/utils.service";
import {NgClass, AsyncPipe} from "@angular/common";
import {RFileUploadStatusComponent} from "../rfile-upload-status/r-file-upload-status.component";
import {RFilesUploadStatusComponent} from "../rfiles-upload-status/r-files-upload-status.component";
import {TranslateModule} from "@ngx-translate/core";
import {TranslatorPipe} from "@app/shared/pipes/translate";

@Component({
    selector: "src-rfile-upload-button",
    templateUrl: "./r-file-upload-button.component.html",
    viewProviders: [{ provide: ControlContainer, useExisting: NgForm }],
    standalone: true,
    imports: [NgxFlowModule, NgClass, FormsModule, RFileUploadStatusComponent, RFilesUploadStatusComponent, AsyncPipe, TranslateModule, TranslatorPipe]
})
export class RFileUploadButtonComponent implements AfterViewInit, OnInit, OnDestroy {
  private cdr = inject(ChangeDetectorRef);
  private utilsService = inject(UtilsService);
  protected appDataService = inject(AppDataService);
  protected authenticationService = inject(AuthenticationService);


  @Input() fileUploadUrl: string;
  @Input() formUploader: boolean = true;
  @Input() uploads: { [key: string]: any };
  @Input() field: Field | undefined = undefined;
  @Input() file_id: string;
  @Input() entry: any;
  @Output() notifyFileUpload: EventEmitter<any> = new EventEmitter<any>();
  @ViewChild("flow") flow: FlowDirective;

  autoUploadSubscription: Subscription;
  fileInput: string;
  showError: boolean = false;
  errorFile: Transfer;
  confirmButton = false;
  flowConfig: FlowOptions;
  fileModel: File | null = null;

  ngOnInit(): void {
    this.file_id = this.file_id ? this.file_id:"status_page";

    this.flowConfig = this.utilsService.getFlowOptions();
    this.flowConfig.target = this.fileUploadUrl;
    this.flowConfig.singleFile = (this.field !== undefined && !this.field.multi_entry);
    this.flowConfig.query = {reference_id: this.field ? this.field.id:""};

    this.fileInput = this.field ? this.field.id : "status_page";
  }

  ngAfterViewInit() {
    this.autoUploadSubscription = this.flow.transfers$.subscribe((event,) => {
      this.confirmButton = false;
      this.showError = false;

      event.transfers.forEach((file)=> {
        if (file.paused && this.errorFile) {
          this.errorFile.flowFile.cancel();
          return;
        }
        if (this.appDataService.public.node.maximum_filesize < (file.size / 1000000)) {
          this.showError = true;
          this.cdr.detectChanges();
          file.flowFile.pause();
          this.errorFile = file;
        } else if (!file.complete) {
          this.confirmButton = true;
        }
      });

      if (this.uploads) {
        this.uploads[this.fileInput] = this.flow;
        this.notifyFileUpload.emit(this.uploads);
      }
    });
  }

  receiveData(data: any) {
    if(this.flow.flowJs.files.length == 0){
      this.fileModel = data;
    }
  }

  ngOnDestroy() {
    this.autoUploadSubscription.unsubscribe();
  }

  onConfirmClick() {
    if (!this.flow.flowJs.isUploading()) {
      this.flow.upload();
    }
  }

  protected dismissError() {
    this.showError = false;
  }
}
