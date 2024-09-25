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

  uploadedFiles: FileItem[] = [];

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
        { tid: 1, name: 'OE 01' },
        { tid: 11, name: 'OE 02' },
        { tid: 21, name: 'OE 03' },
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
      ];
    }, 500);
  }


  addOrganization(event: Event) {
    const selectElement = event.target as HTMLSelectElement;
    const oe_id = parseInt(selectElement.value);

    if (oe_id) {
      const selected = this.organizations.find(org => org.tid == oe_id);
      if (selected && !this.selectedOrganizations.includes(selected)) {
        this.selectedOrganizations.push(selected);
      }
    }
  }
  
  removeOrganization(oe_id: number) {
    this.selectedOrganizations = this.selectedOrganizations.filter(org => org.tid != oe_id);
  }

  selectReviewForm(event: Event) {
    const selectElement = event.target as HTMLSelectElement;
    const formId = selectElement.value;
    this.selectedReviewForm = this.reviewForms.find(form => form.form_id === formId) || null;
  }

  // // Events
  // onFileUploaded(newFile: FileItem) {
  //   this.files.push(newFile);
  //   this.checkingFile = true;
  // }

  // onFileVerified(status: string) {
  //   this.checkingFile = false;
  //   // TODO: Set checkbox checked for newly added files
  // }

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
    if (this.isFormValid()) {
      // TODO: Add API call
      console.log("Form inviato!");
    }
  }
}
