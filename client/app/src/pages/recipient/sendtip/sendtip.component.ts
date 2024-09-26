import { Component, OnInit } from '@angular/core';
import {Location} from '@angular/common';
import { FileItem, SendTip } from "@app/models/reciever/sendtip-data";
import { HttpService } from '@app/shared/services/http.service';
import { questionnaireResolverModel } from '@app/models/resolvers/questionnaire-model';
import { tenantResolverModel } from '@app/models/resolvers/tenant-resolver-model';

@Component({
  selector: "src-sendtip",
  templateUrl: "./sendtip.component.html",
})
export class SendtipComponent implements OnInit {
  organizations: tenantResolverModel[] = [];
  reviewForms: questionnaireResolverModel[] = [];
  files: FileItem[] = [];

  sendTipRequest: SendTip = new SendTip();

  selectedOrganizations: tenantResolverModel[] = [];
  selectedReviewFormId: string | null = null;

  checkingFile: boolean = false;

  uploadedFiles: FileItem[] = [];

  constructor(private _location: Location, private httpService: HttpService){}

  backClicked() {
    this._location.back();
  }

  ngOnInit(): void {
    this.loadOrganizations();
    this.loadReviewForms();
    this.loadFiles();
  }

  loadOrganizations() {

    return this.httpService.fetchTenant().subscribe((response: tenantResolverModel[]) =>{
        this.organizations = response
    });
  }



  loadReviewForms() {
      return this.httpService.requestQuestionnairesResource().subscribe((response: questionnaireResolverModel[]) => {
        this.reviewForms = response;
      });
  }

  loadFiles() {
    setTimeout(() => {
      this.files = [
        { id: 'uuid-1', name: 'file1.txt', scanStatus: 'Verificato', origin: 'Segnalante', uploadDate: '01-01-2023 12:00', size: '1 KB', infected: false, loading: false },
        { id: 'uuid-2', name: 'file2.txt', scanStatus: 'Verificato', origin: 'Organizzazione Esterna', uploadDate: '02-01-2023 13:00', size: '2 KB', infected: false, loading: false },
        { id: 'uuid-3', name: 'file3.txt', scanStatus: 'Verificato', origin: 'Istruttore', uploadDate: '03-01-2023 14:00', size: '3 KB', infected: false, loading: false },
      ];
    }, 500);
  }


  addOrganization(selectElement: HTMLSelectElement) {
    const oe_id = parseInt(selectElement.value);

    if (oe_id) {
      const selected = this.organizations.find(org => org.id == oe_id);
      if (selected && !this.selectedOrganizations.includes(selected)) {
        this.selectedOrganizations.push(selected);
        this.sendTipRequest.tids.push(selected.id)
      }
    }
  }

  removeOrganization(oe_id: number) {
    this.selectedOrganizations = this.selectedOrganizations.filter(org => org.id != oe_id);
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
      this.sendTipRequest.questionnaire_id !== null &&
      this.sendTipRequest.files.length > 0 &&
      this.sendTipRequest.text.trim().length > 0
    );
  }

  sendForm() {
    if (this.isFormValid()) {
      //todo: lista dei file solo come id-origin???
      console.log("Form :" , this.sendTipRequest);
      console.log("todo: inviare file appena caricati")
    }
  }
}
