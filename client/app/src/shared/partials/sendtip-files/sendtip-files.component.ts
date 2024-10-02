import { Component, Input, OnInit } from "@angular/core";
import { RFile, WbFile } from "@app/models/app/shared-public-model";
import { AttachmentFile, FileItem } from "@app/models/reciever/sendtip-data";
import { ReceiverTipService } from "@app/services/helper/receiver-tip.service";
import { TranslateService } from "@ngx-translate/core";

@Component({
  selector: "sendtip-files",
  templateUrl: "./sendtip-files.component.html"
})
export class SendtipFilesComponent implements OnInit {
  @Input() files: FileItem[] = []; // TODO: mock data to be removed
  @Input() selectedFiles: AttachmentFile[] = [];

  @Input() isSelectable: boolean = true;
  rfiles: RFile[];
  wbfiles: WbFile[];
  filesToDisplay: FileItem[] = [];
  

  constructor(private rtipService: ReceiverTipService, private translate: TranslateService) {
    this.rfiles = rtipService.tip.rfiles;
    this.wbfiles = rtipService.tip.wbfiles;
    this.prepareFilesToDisplay();
  }

  ngOnInit(): void {
  }

  toggleFileSelection(file: FileItem) {
    const index = this.selectedFiles.findIndex(f => f.id === file.id);
    if (index > -1) {
      this.selectedFiles.splice(index, 1);
    } else {
      this.selectedFiles.push(file);
    }
  }
  
  prepareFilesToDisplay(): void {
    const rfilesMapped = this.rfiles
      .filter(file => file.visibility !== 'personal' /*&& file.state === 'verificato'*/) // TODO: da scommentare appena si aggiunge file.state
      .map(file => ({
        id: file.id,
        name: file.name,
        scanStatus: '-', // TODO per il momento trattino poi file.state
        origin: this.mapVisibility(file.visibility),
        uploadDate: file.creation_date,
        size: file.size.toString(),
        infected: false, // TODO per il momento false
        loading: false, // TODO per il momento false
        file: undefined // TODO per download file
    }));

    // Mappiamo wbfiles aggiungendo scanStatus, origin e altre proprietà richieste
    const wbfilesMapped = this.wbfiles
      //.filter(file => file.state === 'verificato') // TODO: da scommentare appena si aggiunge file.state
      .map(file => ({
        id: file.id,
        name: file.name,
        scanStatus: '-', // TODO per il momento trattino poi file.state
        origin: this.translate.instant('Whistleblower'), // TODO add traslation?
        uploadDate: file.creation_date,
        size: file.size.toString(),
        infected: false, // TODO per il momento false
        loading: false, // TODO per il momento false
        file: undefined // TODO per download file
    }));

    // Uniamo gli array
    this.filesToDisplay = [...rfilesMapped, ...wbfilesMapped];
  }

  mapVisibility(visibility: string): string { // TODO: manage translations
    switch (visibility) {
      case 'public':
      case 'internal':
        return this.translate.instant('Instructor');
      case 'oe':
        return this.translate.instant('External Organization');
      default:
        return 'UNKNOWN';
    }
  }
}
