import { Component, OnInit } from '@angular/core';
import {Location} from '@angular/common';
import { FileItem, SentTipDetail } from "@app/models/reciever/sendtip-data";

@Component({
  selector: "src-sendtip-detail",
  templateUrl: "./sendtip-detail.component.html",
})
export class SendtipDetailComponent implements OnInit {
  detail: SentTipDetail | null = null;
  files: FileItem[] = [];

  constructor(private _location: Location){}

  backClicked() {
    this._location.back();
  }

  ngOnInit(): void {
    this.loadDetail();
    this.loadFiles();
  }

  loadDetail() {
    setTimeout(() => {
      this.detail = {
        organization: 'Organizzazione 01',
        date: '01-01-2023',
        fileSent: 5,
        status: 'Open',
        text: 'Example text content',
        review_form: { field1: 'value1', field2: 'value2' },
      };
    }, 500);
  }

  loadFiles() {
    setTimeout(() => {
      this.files = [
        { id: 'uuid-1', name: 'file1.txt', scanStatus: 'Verificato', origin: 'Segnalante', uploadDate: '01-01-2023 12:00', size: '1 KB', infected: false, loading: false },
        { id: 'uuid-2', name: 'file2.txt', scanStatus: 'Verificato', origin: 'Organizzazione Esterna', uploadDate: '02-01-2023 13:00', size: '2 KB', infected: false, loading: false },
        { id: 'uuid-3', name: 'file3.txt', scanStatus: 'Verificato', origin: 'Istruttore', uploadDate: '03-01-2023 14:00', size: '3 KB', infected: false, loading: false },
        { id: 'uuid-4', name: 'file4.txt', scanStatus: 'Verificato', origin: 'Nuovo', uploadDate: '04-01-2023 15:00', size: '4 KB', infected: false, loading: false },
      ];
    }, 500);
  }

  onFileUploaded(newFile: FileItem) {
    this.files.push(newFile);
  }

  onFileVerified(verifiedStatus: string) {
    console.log('File verificato:', verifiedStatus);
  }

  onFileDeleted(deletedFile: FileItem) {
    this.files = this.files.filter(file => file.id !== deletedFile.id);
  }
}
