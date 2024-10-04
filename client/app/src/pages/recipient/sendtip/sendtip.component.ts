import { Component, OnInit } from '@angular/core';
import {Location} from '@angular/common';
import { FileItem, SendTip } from "@app/models/reciever/sendtip-data";
import { HttpService } from '@app/shared/services/http.service';
import { questionnaireResolverModel } from '@app/models/resolvers/questionnaire-model';
import { tenantResolverModel } from '@app/models/resolvers/tenant-resolver-model';
import { Forwarding } from '@app/models/reciever/reciever-tip-data';
import { ReceiverTipService } from '@app/services/helper/receiver-tip.service';

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

  constructor(private _location: Location, private httpService: HttpService,
    private rtipService: ReceiverTipService){
      this.sendTipRequest.tip_id = this.rtipService.tip.id;
    }

  backClicked() {
    this._location.back();
  }

  ngOnInit(): void {
    this.loadOrganizations();
    this.loadReviewForms();
    // this.loadFiles();
  }

  loadOrganizations() {

    return this.httpService.fetchTenant().subscribe((response: tenantResolverModel[]) =>{
      this.organizations = response.map(v => { return {name: v.name, tid: v.id} }) as Forwarding[];
    });
  }



  loadReviewForms() {
      return this.httpService.requestQuestionnairesResource().subscribe((response: questionnaireResolverModel[]) => {
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


  // Form validation and send
  isFormValid(): boolean {
    return (
      this.sendTipRequest.tids.length > 0 &&
      this.sendTipRequest.questionnaire_id != null &&
      // this.sendTipRequest.files.length > 0 && // TODO: check if files are required
      this.sendTipRequest.text?.trim().length > 0
    );
  }

  sendForm() {
    if (this.isFormValid()) {
      this.httpService.sendTipRequest(this.sendTipRequest).subscribe({
        next: () => {
          // TODO: redirect to the moon
        },
        error: (err) => {
          console.error("Errore durante l'inoltro della segnalazione'", err);
        }
      }); 
    }
  }
}
