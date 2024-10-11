import { Component, EventEmitter, Input, OnInit, Output } from "@angular/core";
import { RFile, WbFile } from "@app/models/app/shared-public-model";
import { RecieverTipData } from "@app/models/reciever/reciever-tip-data";
import { AttachmentFile, FileItem } from "@app/models/reciever/sendtip-data";
import { ReceiverTipService } from "@app/services/helper/receiver-tip.service";
import { TranslateService } from "@ngx-translate/core";

@Component({
  selector: "sendtip-files",
  templateUrl: "./sendtip-files.component.html"
})
export class SendtipFilesComponent implements OnInit {
  @Input() tip: RecieverTipData;
  @Input() selectedFiles: AttachmentFile[] = [];
  @Input() isSelectable: boolean = true;
  @Output() selectedFilesChange = new EventEmitter<AttachmentFile[]>();
  rfiles: RFile[];
  wbfiles: WbFile[];
  files: FileItem[] = [];
  

  constructor(private translate: TranslateService) {}

  ngOnInit(): void {
    this.rfiles = this.tip.rfiles;
    this.wbfiles = this.tip.wbfiles;
    this.prepareFilesToDisplay();
  }

  toggleFileSelection(file: FileItem) {
    const index = this.selectedFiles.findIndex(f => f.id === file.id);
    if (index > -1) {
      this.selectedFiles.splice(index, 1);
    } else {
      const { id, origin } = file;
      this.selectedFiles.push({ id, origin });
    }
    this.selectedFilesChange.emit(this.selectedFiles);
  }
  
  prepareFilesToDisplay(): void {
    // Mappiamo rfiles aggiungendo scanStatus, origin e altre proprietà richieste
    const rfilesMapped = this.rfiles
      .filter(file => file.visibility !== 'personal' /*&& file.status === 'VERIFIED'*/) // TODO: da scommentare appena si aggiunge file.state
      .map(file => ({
        id: file.id,
        name: file.name,
        status: file.status, //TODO "INFECTED",
        origin: this.mapVisibility(file.visibility, 'file.authorType'), // TODO: da implementare file.authorType
        uploadDate: file.creation_date,
        size: file.size.toString(),
        file: undefined, // TODO per download file
        verification_date: file.verification_date
    }));

    // Mappiamo wbfiles aggiungendo scanStatus, origin e altre proprietà richieste
    const wbfilesMapped = this.wbfiles
      //.filter(file => file.status === 'VERIFIED') // TODO: da scommentare appena si aggiunge file.state
      .map(file => ({
        id: file.id,
        name: file.name,
        status: file.status,
        origin: this.translate.instant('Whistleblower'), // TODO add traslation?
        uploadDate: file.creation_date,
        size: file.size.toString(),
        file: undefined, // TODO per download file
        verification_date: file.verification_date
    }));

    // Uniamo gli array
    this.files = [...rfilesMapped, ...wbfilesMapped];
  }

  mapVisibility(visibility: string, authorType: string): string {
    switch (visibility) {
      case 'public':
      case 'internal':
        return this.translate.instant('Instructor');
      case 'oe':
        if (authorType === 'anac') { // TODO: da implementare file.authorType
          return this.translate.instant('To External Organization');
        } else {
          return this.translate.instant('By External Organization');
        }
      default:
        return 'UNKNOWN';
    }
  }
}
