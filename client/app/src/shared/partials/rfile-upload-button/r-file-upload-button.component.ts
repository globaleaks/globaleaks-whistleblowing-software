import {
  AfterViewInit,
  ChangeDetectorRef,
  Component,
  EventEmitter,
  Input, OnDestroy,
  OnInit,
  Output,
  ViewChild
} from "@angular/core";
import {FlowDirective, Transfer} from "@flowjs/ngx-flow";
import {AppDataService} from "@app/app-data.service";
import {ControlContainer, NgForm} from "@angular/forms";
import {Subscription} from "rxjs";
import {FlowOptions} from "@flowjs/flow.js";
import {Field} from "@app/models/resolvers/field-template-model";
import { AuthenticationService } from "@app/services/helper/authentication.service";
import { UtilsService } from "@app/shared/services/utils.service";

@Component({
  selector: "src-rfile-upload-button",
  templateUrl: "./r-file-upload-button.component.html",
  viewProviders: [{provide: ControlContainer, useExisting: NgForm}]
})
export class RFileUploadButtonComponent implements AfterViewInit, OnInit, OnDestroy {

  @Input() fileUploadUrl: string;
  @Input() formUploader: boolean = true;
  @Input() uploads: { [key: string]: any };
  @Input() field: Field | undefined = undefined;
  @Input() file_id: string;
  @Output() notifyFileUpload: EventEmitter<any> = new EventEmitter<any>();
  @ViewChild("flow") flow: FlowDirective;

  @Input() customQuery: any;

  autoUploadSubscription: Subscription;
  fileInput: string;
  showError: boolean = false;
  errorFile: Transfer;
  confirmButton = false;
  flowConfig: FlowOptions;

  constructor(private cdr: ChangeDetectorRef, private utilsService: UtilsService, protected appDataService: AppDataService,protected authenticationService:AuthenticationService) {
  }

  ngOnInit(): void {
    this.file_id = this.file_id ? this.file_id:"status_page";
    this.flowConfig = this.utilsService.flowDefault.opts;

    this.flowConfig.target = this.fileUploadUrl;
    this.flowConfig.singleFile = (this.field !== undefined && !this.field.multi_entry);
    this.flowConfig.query = this.customQuery ? this.customQuery : {reference_id: this.field ? this.field.id:""};
    this.flowConfig.headers = {"X-Session": this.authenticationService.session.id};
    this.fileInput = this.field ? this.field.id : "status_page";
  }

  ngAfterViewInit() {
    this.autoUploadSubscription = this.flow.transfers$.subscribe((event,) => {

      this.confirmButton = false;
      this.showError = false;

      if (!this.uploads) {
        this.uploads = {};
      }
      if (this.uploads && !this.uploads[this.fileInput]) {
        this.uploads[this.fileInput] = [];
      }
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
      this.flow.flowJs.opts.headers={"X-Session": this.authenticationService.session.id};
      this.uploads[this.fileInput] = this.flow;
      this.notifyFileUpload.emit(this.uploads);
    });
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
