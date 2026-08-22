import {AfterViewInit, ChangeDetectorRef, Component, OnDestroy, OnInit, inject, input, viewChild, output} from "@angular/core";
import {RenderSchedulerService} from "@app/shared/services/render-scheduler.service";
import {FlowConfig, Transfer, NgxFlowModule} from "@flowjs/ngx-flow";
import {AppDataService} from "@app/app-data.service";
import {ControlContainer, FormsModule, NgForm} from "@angular/forms";
import {Subscription} from "rxjs";
import {FlowOptions} from "@flowjs/flow.js";
import {Field} from "@app/models/resolvers/field-template-model";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {UtilsService} from "@app/shared/services/utils.service";
import {AsyncPipe} from "@angular/common";
import {RFileUploadStatusComponent} from "../rfile-upload-status/r-file-upload-status.component";
import {RFilesUploadStatusComponent} from "../rfiles-upload-status/r-files-upload-status.component";
import {TranslateModule} from "@ngx-translate/core";

@Component({
    selector: "src-rfile-upload-button",
    templateUrl: "./r-file-upload-button.component.html",
    viewProviders: [{ provide: ControlContainer, useExisting: NgForm }],
    standalone: true,
    imports: [NgxFlowModule, FormsModule, RFileUploadStatusComponent, RFilesUploadStatusComponent, AsyncPipe, TranslateModule]
})
export class RFileUploadButtonComponent implements AfterViewInit, OnInit, OnDestroy {
  private renderScheduler = inject(RenderSchedulerService);
  private cdr = inject(ChangeDetectorRef);
  private utilsService = inject(UtilsService);
  protected appDataService = inject(AppDataService);
  protected authenticationService = inject(AuthenticationService);


  readonly fileUploadUrl = input<string>();
  readonly formUploader = input(true);
  readonly uploads = input<Record<string, any>>();
  readonly field = input<Field>();
  readonly file_id = input<string>();
  readonly entry = input<any>();
  readonly notifyFileUpload = output<any>();
  readonly flow = viewChild.required<FlowConfig>("flow");

  autoUploadSubscription: Subscription;
  fileInput: string;
  showError = false;
  errorFile: Transfer;
  confirmButton = false;
  flowConfig: FlowOptions;
  fileModel: File | null = null;

  ngOnInit(): void {
    const field = this.field();
    const fieldValue = this.field();
    const entry = this.entry();
    this.flowConfig = this.utilsService.getFlowOptions({
      target: this.fileUploadUrl(),
      singleFile: (field !== undefined && !field.multi_entry),
      query: {reference_id: fieldValue && entry.index !== undefined  ? `${fieldValue.id}-${entry.index}`  : fieldValue ? fieldValue.id : ""}
    });

    this.fileInput = this.file_id() || "status_page";
  }

  ngAfterViewInit() {
    this.autoUploadSubscription = this.flow().transfers$.subscribe((event,) => {
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
          this.renderScheduler.schedule();
        }
      });

      const uploads = this.uploads();
      if (uploads) {
        (this.flow() as any).field = this.field();
        uploads[this.fileInput] = this.flow();
        this.notifyFileUpload.emit(uploads);
      }
    });
  }

  receiveData(data: any) {
    if(this.flow().flowJs.files.length == 0){
      this.fileModel = data;
    }
  }

  ngOnDestroy() {
    this.autoUploadSubscription.unsubscribe();
  }

  onConfirmClick() {
    const flow = this.flow();
    if (!flow.flowJs.isUploading()) {
      flow.upload();
    }
  }

  protected dismissError() {
    this.showError = false;
  }
}
