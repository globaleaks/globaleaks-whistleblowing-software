import { Component, EventEmitter, Input, Output } from '@angular/core';
import { FileItem } from '@app/models/reciever/sendtip-data';
import { AuthenticationService } from '@app/services/helper/authentication.service';
import { UtilsService } from '@app/shared/services/utils.service';

@Component({
  selector: 'sendtip-file-upload',
  templateUrl: './sendtip-file-upload.component.html'
})
export class SendTipFileUploadComponent {


  @Input() files: FileItem[] = [];
  @Output() filesChange = new EventEmitter<FileItem[]>();

  collapsed = false;

  newFileDescription: string = "";

  constructor(protected utilsService: UtilsService, protected authenticationService: AuthenticationService){}

  addFile(event: any) {

    const file: File = event.target.files[0];

    if (file) {

      let item: FileItem = {
        file: file,
        description: this.newFileDescription,
        id: 'uuid-' + (Math.random() * 10000).toFixed(0),
        name: file.name,
        scanStatus: 'PENDING', // Status iniziale
        origin: 'recipient',
        uploadDate: new Date().toLocaleString(),
        size: `${file.size}`,
        infected: false,
        loading: true
      }
    
      this.files.push(item);
      this.filesChange.emit(this.files);
      this.newFileDescription = "";
    
    }
  }


  removeFile(index: number){
    this.files.splice(index, 1);
    this.filesChange.emit(this.files);
  }
}
