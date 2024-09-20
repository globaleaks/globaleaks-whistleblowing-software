import { Component, EventEmitter, Input, Output } from '@angular/core';
import { FileItem } from '@app/models/reciever/sendtip-data';
import { UtilsService } from '@app/shared/services/utils.service';

@Component({
  selector: 'sendtip-file-upload',
  templateUrl: './sendtip-file-upload.component.html'
})
export class SendTipFileUploadComponent {


  @Input() files: FileItem[] = [];

  collapsed = false;

  checkingFile: boolean = false;

  constructor(protected utilsService: UtilsService){}

  addFile(fileInput: HTMLInputElement) {


    const file = fileInput.files?.[0];

    if (file) {
      const loadingFile: FileItem = {
        id: 'uuid-' + (Math.random() * 10000).toFixed(0),
        name: file.name,
        scanStatus: 'In attesa', // Status iniziale
        origin: 'Nuovo',
        uploadDate: new Date().toLocaleString(),
        size: `${file.size} bytes`,
        infected: false,
        loading: true
      };

      this.files.push(loadingFile);

      // this.fileUploaded.emit(loadingFile);

      // setTimeout(() => {
      //   loadingFile.scanStatus = 'Verificato';
      //   loadingFile.loading = false;
      //   this.checkingFile = false;
      //   this.fileVerified.emit(loadingFile.scanStatus)
      // }, 3000);
    }
  }
}
