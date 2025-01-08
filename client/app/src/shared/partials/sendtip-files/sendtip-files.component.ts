import { Component, EventEmitter, Input, OnInit, Output } from "@angular/core";
import { RFile, WbFile } from "@app/models/app/shared-public-model";
import { FileReference, RecieverTipData } from "@app/models/reciever/reciever-tip-data";
import { AttachmentFile, FileItem } from "@app/models/reciever/sendtip-data";
import { UtilsService } from "@app/shared/services/utils.service";

@Component({
  selector: "sendtip-files",
  templateUrl: "./sendtip-files.component.html"
})
export class SendtipFilesComponent implements OnInit {
  @Input() tip: RecieverTipData;
  @Input() selectedFiles: AttachmentFile[] = [];
  @Input() isSelectable: boolean = true;
  @Input() canDownloadInfected: boolean = false;
  @Input() isAntivirusEnable: boolean = false;

  @Input() forwardingDetailFiles: FileReference[];

  @Output() selectedFilesChange = new EventEmitter<AttachmentFile[]>();
  rfiles: RFile[];
  wbfiles: WbFile[];
  files: FileItem[] = [];


  constructor(protected utilsService: UtilsService){}
  
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
    const rfilesFiltered = this.rfiles.filter(file => 
      file.visibility !== 'personal'
    );

    const rfilesMapped = rfilesFiltered
      .map(file => ({
        id: file.id,
        name: file.name,
        status: file.status, 
        origin: this.mapVisibility(file.visibility, 'file.authorType'), 
        uploadDate: file.creation_date,
        size: file.size,
        verification_date: file.verification_date,
        download_url: "api/recipient/rfiles/"+file.id
    }));

    const wbfilesMapped = this.wbfiles.map(file => ({
      id: file.ifile_id,
      name: file.name,
      status: file.status,
      origin: 'whistleblower',
      uploadDate: file.creation_date,
      size: file.size,
      verification_date: file.verification_date,
      download_url: "api/recipient/wbfiles/"+file.id
    }));


    this.files = [...rfilesMapped, ...wbfilesMapped];

    if(this.forwardingDetailFiles){
      this.files = this.files.filter(file => this.forwardingDetailFiles.some(i => i?.id === file.id))
    }
  }

  mapVisibility(visibility: string, authorType: string): string {
    switch (visibility) {
      case 'public':
      case 'internal':
        return 'recipient'
      case 'eo':
        if (authorType === 'main') {
          return 'recipient';
        } else {
          return 'eo';
        }
      default:
        return 'UNKNOWN';
    }
  }

}
