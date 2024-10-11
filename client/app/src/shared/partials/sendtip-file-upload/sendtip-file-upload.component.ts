import { ChangeDetectorRef, Component, EventEmitter, ElementRef, Input, Output, ViewChild } from '@angular/core';
import { AppDataService } from '@app/app-data.service';
import { RecieverTipData } from '@app/models/reciever/reciever-tip-data';
import { FileItem } from '@app/models/reciever/sendtip-data';
import { AuthenticationService } from '@app/services/helper/authentication.service';
import { HttpService } from '@app/shared/services/http.service';
import { UtilsService } from '@app/shared/services/utils.service';

@Component({
  selector: 'sendtip-file-upload',
  templateUrl: './sendtip-file-upload.component.html'
})
export class SendTipFileUploadComponent {

  @ViewChild('uploader') uploaderInput: ElementRef<HTMLInputElement>;

  @Input() files: FileItem[] = [];

  @Input() tip: RecieverTipData
  @Output() filesChange = new EventEmitter<FileItem[]>();

  collapsed = false;

  newFileDescription: string = "";

  constructor(protected utilsService: UtilsService, protected authenticationService: AuthenticationService, protected appDataService: AppDataService, private cdr: ChangeDetectorRef, protected httpService: HttpService) { }

  addFile(files: FileList | null) {

    if (files && files.length > 0) {
      const file = files[0];


      if (this.tip) {
        const flowJsInstance = this.utilsService.flowDefault;

        this.files = [];

        flowJsInstance.opts.target = "api/recipient/rtips/" + this.tip.id + "/rfiles";
        flowJsInstance.opts.singleFile = true;
        flowJsInstance.opts.query = { description: this.newFileDescription, visibility: "oe", fileSizeLimit: this.appDataService.public.node.maximum_filesize * 1024 * 1024, tids: null };
        flowJsInstance.opts.headers = { "X-Session": this.authenticationService.session.id };
        flowJsInstance.on("fileSuccess", (_, message) => {
          
          let response = JSON.parse(message);

          this.files.push({
            file: file,
            description: this.newFileDescription,
            id: response.id,
            name: file.name,
            status: 'PENDING', // Status iniziale
            origin: 'recipient',
            uploadDate: new Date().toLocaleString(),
            size: `${file.size}`
          });
          this.newFileDescription = "";
        });
        flowJsInstance.on("fileError", (file, _) => {
          if (this.uploaderInput) {
            this.uploaderInput.nativeElement.value = "";
          }
          this.cdr.detectChanges();
        });

        this.utilsService.onFlowUpload(flowJsInstance, file);
      }
      else {
      let item: FileItem = {
        file: file,
        description: this.newFileDescription,
        id: 'uuid-' + (Math.random() * 10000).toFixed(0),
        name: file.name,
        status: 'PENDING', // Status iniziale
        origin: 'recipient',
        uploadDate: new Date().toLocaleString(),
        size: `${file.size}`
      }
      this.files.push(item);
      this.filesChange.emit(this.files);
      this.newFileDescription = "";
    
    }
  }
}


  removeFile(index: number) {
    if (this.tip && this.authenticationService.session.role === "receiver") {
      this.httpService.deleteDBFile(this.files[index].id).subscribe (
        {
          next: async _ => {
            // this.dataToParent.emit(wbFile)
            this.files.splice(index, 1);
          }
        }
      );

    }
    else
      this.files.splice(index, 1);
    this.filesChange.emit(this.files);
  }


}
