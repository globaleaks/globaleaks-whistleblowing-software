import { Component, EventEmitter, Input, Output } from '@angular/core';
import { FileItem } from '@app/models/reciever/sendtip-data';

@Component({
  selector: 'src-sendtip-details-files',
  templateUrl: './sendtip-details-files.component.html'
})
export class SendtipDetailFilesComponent {

  @Input() files: FileItem[] = [];
  @Output() fileUploaded = new EventEmitter<FileItem>();
  @Output() fileVerified = new EventEmitter<string>();
  @Output() fileDeleted = new EventEmitter<FileItem>();

  checkingFile: boolean = false;

  addFile(fileInput: HTMLInputElement) {
    this.checkingFile = true;
    const file = fileInput.files?.[0];
    if (file) {
      const loadingFile: FileItem = {
        id: 'uuid-' + (Math.random() * 10000).toFixed(0),
        name: file.name,
        status: 'In attesa',
        origin: 'Nuovo',
        uploadDate: new Date().toLocaleString(),
        size: `${file.size} bytes`
      };

      this.fileUploaded.emit(loadingFile);

      setTimeout(() => {
        loadingFile.status = 'Verificato';
        this.checkingFile = false;
        this.fileVerified.emit(loadingFile.status)
      }, 3000);
    }
  }

  deleteFile(file: FileItem) {
    const index = this.files.findIndex(f => f.id === file.id);
    if (index > -1) {
      this.files.splice(index, 1);
      this.fileDeleted.emit(file);
    }
  }
}
