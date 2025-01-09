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

  constructor(protected utilsService: UtilsService, protected authenticationService: AuthenticationService, protected appDataService: AppDataService, private cdr: ChangeDetectorRef, protected httpService: HttpService) { }

  addFile(files: FileList | null) {

    if (files && files.length > 0) {
      console.log("addFile - files: ", files);
      const file = files[0];
      let item: FileItem = {
        file: file,
        description: '',
        id: 'uuid-' + (Math.random() * 10000).toFixed(0),
        name: file.name,
        status: 'PENDING', 
        origin: 'recipient',
        uploadDate: new Date().toISOString(),
        size: file.size
      }
      this.files.push(item);
      this.filesChange.emit(this.files);
  }
}


  removeFile(index: number) {
    if (this.tip && this.authenticationService.session.role === "receiver") {
      this.httpService.deleteDBFile(this.files[index].id).subscribe (
        {
          next: async _ => {
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
