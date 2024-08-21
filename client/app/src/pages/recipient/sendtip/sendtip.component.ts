import { Component, OnInit } from '@angular/core';
import {Location} from '@angular/common';
import { Organization, ReviewForm, FileItem } from "@app/models/reciever/sendtip-data";

@Component({
  selector: "src-sendtip",
  templateUrl: "./sendtip.component.html",
})
export class SendtipComponent implements OnInit {
  organizations: Organization[] = [];
  reviewForms: ReviewForm[] = [];
  files: FileItem[] = [];

  selectedOrganizations: Organization[] = [];
  selectedReviewForm: ReviewForm | null = null;
  selectedFiles: FileItem[] = [];
  tipText: string = "";

  checkingFile: boolean = false;

  // Initialization

  constructor(private _location: Location){}

  backClicked() {
    this._location.back();
  }

  ngOnInit(): void {
    this.loadOrganizations();
    this.loadReviewForms();
    this.loadFiles();
  }

  loadOrganizations() {
    setTimeout(() => {
      this.organizations = [
        { oe_id: 'uuid-oe1', name: 'OE 01' },
        { oe_id: 'uuid-oe2', name: 'OE 02' },
        { oe_id: 'uuid-oe3', name: 'OE 03' },
      ];
    }, 500);
  }

  loadReviewForms() {
    setTimeout(() => {
      this.reviewForms = [
        { form_id: 'form1', name: 'Form 01' },
        { form_id: 'form2', name: 'Form 02' },
        { form_id: 'form3', name: 'Form 03' },
      ];
    }, 500);
  }

  loadFiles() {
    setTimeout(() => {
      this.files = [
        { id: 'uuid-1', name: 'file1.txt', scanStatus: 'Verificato', origin: 'Segnalante', uploadDate: '01-01-2023 12:00', size: '1 KB', infected: false, loading: false },
        { id: 'uuid-2', name: 'file2.txt', scanStatus: 'Verificato', origin: 'Organizzazione Esterna', uploadDate: '02-01-2023 13:00', size: '2 KB', infected: false, loading: false },
        { id: 'uuid-3', name: 'file3.txt', scanStatus: 'Verificato', origin: 'Istruttore', uploadDate: '03-01-2023 14:00', size: '3 KB', infected: false, loading: false },
        { id: 'uuid-4', name: 'file4.txt', scanStatus: 'Verificato', origin: 'Nuovo', uploadDate: '04-01-2023 15:00', size: '4 KB', infected: false, loading: false },
        { id: 'uuid-5', name: 'file5.txt', scanStatus: 'Infetto', origin: 'Nuovo', uploadDate: '05-01-2023 16:00', size: '5 KB', infected: true, loading: false },
      ];
    }, 500);
  }

  // Logic

  addOrganization(event: Event) {
    const selectElement = event.target as HTMLSelectElement;
    const oe_id = selectElement.value;
  
    if (oe_id) {
      const selected = this.organizations.find(org => org.oe_id === oe_id);
      if (selected && !this.selectedOrganizations.includes(selected)) {
        this.selectedOrganizations.push(selected);
      }
    }
  }
  
  removeOrganization(oe_id: string) {
    this.selectedOrganizations = this.selectedOrganizations.filter(org => org.oe_id !== oe_id);
  }

  selectReviewForm(event: Event) {
    const selectElement = event.target as HTMLSelectElement;
    const formId = selectElement.value;
    this.selectedReviewForm = this.reviewForms.find(form => form.form_id === formId) || null;
  }

  // Events
  onFileUploaded(newFile: FileItem) {
    this.files.push(newFile);
    this.checkingFile = true;
  }

  onFileVerified(status: string) {
    this.checkingFile = false;
    // TODO: Set checkbox checked for newly added files
  }

  // Form validation and send
  isFormValid(): boolean {
    return (
      this.selectedOrganizations.length > 0 &&
      this.selectedReviewForm !== null &&
      this.selectedFiles.length > 0 &&
      this.tipText.trim().length > 0
    );
  }

  sendForm() {
    if (this.isFormValid() && !this.checkingFile) {
      // TODO: Add API call
      console.log("Form inviato!");
    }
  }
}
