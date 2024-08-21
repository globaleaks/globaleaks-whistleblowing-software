import { Component, EventEmitter, Output } from '@angular/core';
import { FileItem } from '@app/models/reciever/sendtip-data';

@Component({
  selector: 'sendtip-file-upload',
  templateUrl: './sendtip-file-upload.component.html'
})
export class SendTipFileUploadComponent {

  @Output() fileUploaded = new EventEmitter<FileItem>();
  @Output() fileVerified = new EventEmitter<string>();

  checkingFile: boolean = false;

  addFile(fileInput: HTMLInputElement) {
    this.checkingFile = true;
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

      this.fileUploaded.emit(loadingFile);

      setTimeout(() => {
        loadingFile.scanStatus = 'Verificato';
        loadingFile.loading = false;
        this.checkingFile = false;
        this.fileVerified.emit(loadingFile.scanStatus)
      }, 3000);
    }
  }
}
