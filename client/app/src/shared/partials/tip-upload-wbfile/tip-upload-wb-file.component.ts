import {Component, Input, ViewChild, ElementRef, ChangeDetectorRef, EventEmitter, Output} from "@angular/core";
import {UtilsService} from "@app/shared/services/utils.service";
import {AppDataService} from "@app/app-data.service";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {Forwarding, RecieverTipData} from "@app/models/reciever/reciever-tip-data";
import {FlowFile} from "@flowjs/flow.js";
import { RFile } from "@app/models/app/shared-public-model";

@Component({
  selector: "src-tip-upload-wbfile",
  templateUrl: "./tip-upload-wb-file.component.html"
})
export class TipUploadWbFileComponent{
  @ViewChild('uploader') uploaderInput: ElementRef<HTMLInputElement>;
  @Input() tip: RecieverTipData;
  @Input() key: string;
  @Input() canUpload: boolean = true;
  @Input() organizations: Forwarding[] = [];

  @Input() onlyNew: boolean = false;

  @Output() dataToParent = new EventEmitter<string>();
  collapsed = false;
  file_upload_description: string = "";
  fileInput: string = "fileinput";
  showError: boolean = false;
  errorFile: FlowFile | null;

  recentFile: RFile;

  newFiles: RFile[] = [];

  constructor(private readonly cdr: ChangeDetectorRef, private readonly authenticationService: AuthenticationService, protected utilsService: UtilsService, protected appDataService: AppDataService) {

  }


  getFilteredAndSortedFiles(files: RFile[]): RFile[] {

    if(this.key === 'oe')
      return files
                .filter(file => file.visibility === this.key)
                .filter(file => this.organizations.map(_=>_.files).flat().some(i => i?.id === file.id))
                .sort((a, b) => new Date(a.creation_date).getTime() - new Date(b.creation_date).getTime());
    else 
      return files
        .filter(file => file.visibility === this.key)
        .sort((a, b) => new Date(a.creation_date).getTime() - new Date(b.creation_date).getTime());
  }



  onFileSelected(files: FileList | null) {
    if (files && files.length > 0) {
      
      const file = files[0];
      this.recentFile = {
        id: this.tip.id,
        creation_date: new Date().toISOString(),
        name: file.name,
        size: file.size,
        type: '',
        description: this.file_upload_description,
        visibility: this.key,
        error: false,
        author: '',
        downloads: 0,
        status: 'PENDING',
        isLoading: true,
        verification_date: null
      };
      

      const flowJsInstance = this.utilsService.flowDefault;

      let tids = this.organizations.map(_=> _.tid);

      flowJsInstance.opts.target = "api/recipient/rtips/" + this.tip.id + "/rfiles";
      flowJsInstance.opts.singleFile = true;
      flowJsInstance.opts.query = {description: this.file_upload_description, visibility: this.key, fileSizeLimit: this.appDataService.public.node.maximum_filesize * 1024 * 1024, tids: "["+tids.toString()+"]"};
      flowJsInstance.opts.headers = {"X-Session": this.authenticationService.session.id};
      flowJsInstance.on("fileSuccess", (_) => {

        this.tip.rfiles.push(this.recentFile);

        if(this.onlyNew && !this.newFiles.includes(this.recentFile)){
          this.newFiles.push(this.recentFile);
        }

        this.recentFile.isLoading = false   

        this.organizations.forEach(org => org.files?.push({"id": this.recentFile.id, "author_type":"main"}))

        this.dataToParent.emit();
        this.errorFile = null;
      });
      flowJsInstance.on("fileError", (file, _) => {
        const index = this.tip.rfiles.indexOf(this.recentFile);
        if (index > -1) {
          this.tip.rfiles.splice(index, 1);
        }
        this.showError = true;
        this.errorFile = file;
        if (this.uploaderInput) {
          this.uploaderInput.nativeElement.value = "";
        }
        this.cdr.detectChanges();
      });

      this.utilsService.onFlowUpload(flowJsInstance, file);
    }
  }

  listenToWbfiles(files: string) {
    this.utilsService.deleteResource(this.tip.rfiles, files);
    this.dataToParent.emit()
  }

  protected dismissError() {
    this.showError = false;
  }




}
