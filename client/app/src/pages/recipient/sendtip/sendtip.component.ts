import { Component, OnInit } from '@angular/core';
import {Location} from '@angular/common';
import { FileItem, SendTip } from "@app/models/reciever/sendtip-data";
import { HttpService } from '@app/shared/services/http.service';
import { questionnaireResolverModel } from '@app/models/resolvers/questionnaire-model';
import { tenantResolverModel } from '@app/models/resolvers/tenant-resolver-model';
import { Forwarding, RecieverTipData } from '@app/models/reciever/reciever-tip-data';
import { ReceiverTipService } from '@app/services/helper/receiver-tip.service';
import { UtilsService } from '@app/shared/services/utils.service';
import { AuthenticationService } from '@app/services/helper/authentication.service';
import { AppDataService } from '@app/app-data.service';
import { PreferenceResolver } from '@app/shared/resolvers/preference.resolver';

@Component({
  selector: "src-sendtip",
  templateUrl: "./sendtip.component.html",
})
export class SendtipComponent implements OnInit {
  organizations: Forwarding[] = [];
  reviewForms: questionnaireResolverModel[] = [];

  sendTipRequest: SendTip = new SendTip();

  selectedOrganizations: Forwarding[] = [];
  selectedReviewFormId: string | null = null;

  checkingFile: boolean = false;

  uploadedFiles: FileItem[] = [];
  tip: RecieverTipData;
  forwardedEOList: Forwarding[] = [];

  data: any;

  constructor(private readonly _location: Location, private readonly httpService: HttpService,
    private readonly rtipService: ReceiverTipService, protected utilsService: UtilsService,
    private readonly authenticationService: AuthenticationService, protected appDataService: AppDataService,
    protected preferenceResolver: PreferenceResolver){
      this.sendTipRequest.tip_id = this.rtipService.tip.id;
      this.tip = this.rtipService.tip;
      this.forwardedEOList = this.tip.forwardings;
    }

  backClicked() {
    this._location.back();
  }

  ngOnInit(): void {
    this.loadOrganizations();
    this.loadReviewForms();
  }

  loadOrganizations() {
    
    return this.httpService.fetchForwardingTenants().subscribe((response: tenantResolverModel[]) =>{
      this.organizations = response
            .filter(v => !this.forwardedEOList.some(eo => eo.tid === v.id))
            .map(v => ({ name: v.name, tid: v.id })) as Forwarding[];
    });
  }



  loadReviewForms() {
    return this.httpService.requestForwardingQuestionnairesResource().subscribe((response: questionnaireResolverModel[]) => {
      this.reviewForms = response;
    });
  }


  addOrganization(eo_id: Forwarding) {

    if (eo_id) {
      const selected = this.organizations.find(org => org.tid == eo_id.tid);
      if (selected && !this.selectedOrganizations.includes(selected)) {
        this.selectedOrganizations.push(selected);
        this.sendTipRequest.tids.push(selected.tid)
      }
    }
  }

  removeOrganization(eo_id: number) {
    this.selectedOrganizations = this.selectedOrganizations.filter(org => org.tid != eo_id);
    this.sendTipRequest.tids = this.sendTipRequest.tids.filter(org => org != eo_id);
  }

  selectReviewForm(event: Event) {
    const selectElement = event.target as HTMLSelectElement;
    this.sendTipRequest.questionnaire_id = selectElement.value;
  }


  isFormValid(): boolean {
    return (
      this.sendTipRequest.tids.length > 0 &&
      this.sendTipRequest.questionnaire_id != null &&
      this.sendTipRequest.text?.trim().length > 0
    );
  }

  sendForm() {
    if (this.isFormValid()) {
      this.httpService.sendTipRequest(this.sendTipRequest).subscribe({
        next: (res) => {
          this.uploadFiles();
          this._location.back();
        },
        error: (err) => {
          console.error("Errore durante l'inoltro della segnalazione'", err);
        }
      }); 
    }
  }

  uploadFiles() {
    if (!this.uploadedFiles || this.uploadedFiles.length === 0) {
      console.log('No files selected for upload.');
      return;
    }

    const flowJsInstance = this.utilsService.flowDefault;
    const sessionId = this.authenticationService.session.id;
    const fileSizeLimit = this.appDataService.public.node.maximum_filesize * 1024 * 1024;

    flowJsInstance.opts.target = "api/recipient/rtips/" + this.tip.id + "/rfiles";
    flowJsInstance.opts.headers = { "X-Session": sessionId };

    flowJsInstance.on("fileSuccess", (file, _) => {
      console.log(`File ${file.name} uploaded successfully.`);
    });

    flowJsInstance.on("fileError", (file, message) => {
      console.error(`Error loading file ${file.name}: ${message}`);
    });

    this.uploadedFiles.forEach((file) => {
      if (file.file) {
        flowJsInstance.opts.query = {
          description: file.description,
          visibility: 'eo',
          fileSizeLimit: fileSizeLimit,
          tids: "[" + this.selectedOrganizations.map(_ => _.tid).toString() + "]"
        };
        
        try {
          flowJsInstance.addFile(file.file);
          flowJsInstance.upload();
        } catch (error) {
          console.error(`Error loading ${file.name}:`, error);
        }
      } else {
        console.warn(`File missing from file list: ${file.name}`);
      }
    });
  }
}
