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

  data: any;

  constructor(private readonly _location: Location, private readonly httpService: HttpService,
    private readonly rtipService: ReceiverTipService, protected utilsService: UtilsService,
    private readonly authenticationService: AuthenticationService, protected appDataService: AppDataService,
    protected preferenceResolver: PreferenceResolver){
      this.sendTipRequest.tip_id = this.rtipService.tip.id;
      this.tip = this.rtipService.tip;
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
      this.organizations = response.map(v => { return {name: v.name, tid: v.id} }) as Forwarding[];
    });
  }



  loadReviewForms() {
    return this.httpService.requestForwardingQuestionnairesResource().subscribe((response: questionnaireResolverModel[]) => {
      this.reviewForms = response;
    });
  }


  addOrganization(oe_id: Forwarding) {

    if (oe_id) {
      const selected = this.organizations.find(org => org.tid == oe_id.tid);
      if (selected && !this.selectedOrganizations.includes(selected)) {
        this.selectedOrganizations.push(selected);
        this.sendTipRequest.tids.push(selected.tid)
      }
    }
  }

  removeOrganization(oe_id: number) {
    this.selectedOrganizations = this.selectedOrganizations.filter(org => org.tid != oe_id);
    this.sendTipRequest.tids = this.sendTipRequest.tids.filter(org => org != oe_id);
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
      console.log('uploadedFiles', this.uploadedFiles);
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
    if (this.uploadedFiles && this.uploadedFiles.length > 0) {
      const flowJsInstance = this.utilsService.flowDefault;

      flowJsInstance.opts.target = "api/recipient/rtips/" + this.tip.id + "/rfiles";;
      flowJsInstance.opts.singleFile = true;
      flowJsInstance.opts.headers = {
        "X-Session": this.authenticationService.session.id
      };

      flowJsInstance.on("fileSuccess", (file, message) => {
        console.log(`File ${file.name} caricato con successo.`);
      });

      flowJsInstance.on("fileError", (file, message) => {
        console.error(`Errore durante il caricamento del file ${file.name}: ${message}`);
      });

      this.uploadedFiles.forEach(file => {
        if (file.file) {
          flowJsInstance.opts.query = {
            description: file.description,
            visibility: 'oe',
            fileSizeLimit: this.appDataService.public.node.maximum_filesize * 1024 * 1024,
            tids: "["+this.selectedOrganizations.map(_=> _.tid).toString()+"]"
          };
  
          flowJsInstance.addFile(file.file);
        }
        
      });

      flowJsInstance.upload();
    } else {
      console.log('Nessun file selezionato per il caricamento.');
    }
  }
}