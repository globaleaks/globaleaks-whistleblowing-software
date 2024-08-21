import { Component, OnInit, ViewChild, TemplateRef } from "@angular/core";
import { AuthenticationService } from "@app/services/helper/authentication.service";
import { Constants } from "@app/shared/constants/constants";
import { ActivatedRoute, Router } from "@angular/router";
import { AppDataService } from "@app/app-data.service";
import { NgbModal } from "@ng-bootstrap/ng-bootstrap";
import { NgForm } from "@angular/forms";

@Component({
  selector: "app-login",
  templateUrl: "./accred.component.html"
})
export class AccredComponent implements OnInit {
  @ViewChild("accredForm") public accredForm: NgForm;
  @ViewChild('content') content: TemplateRef<any>;
  modalMessage = 'A confirmation email will be sent to the organization\'s PEC.';

  protected readonly location = location;
  protected readonly Constants = Constants;

  organizationInfo = {
    denomination: '',
    pec: '',
    confirmPec: '',
    institutionalWebsite: ''
  };
  adminInfo = {
    name: '',
    email: '',
    fiscalCode: ''
  };
  recipientInfo = {
    name: '',
    fiscalCode: '',
    email: ''
  };

  pecsMatch = true;
  privacyAccept = false;
  privacyPolicy = 'Your privacy policy text here...';

  constructor(private authentication: AuthenticationService, public router: Router, private route: ActivatedRoute, protected appDataService: AppDataService, private modalService: NgbModal) {}

  ngOnInit() {
    this.adminInfo.fiscalCode = this.getFiscalCodeFromIdp();
  }

  private getFiscalCodeFromIdp(): string {
    return 'sample-fiscal-code';
  }

  checkPecsMatch() {
    this.pecsMatch = this.organizationInfo.pec === this.organizationInfo.confirmPec;
  }

  closeModal(modal: any) {
    modal.close('Close click');
    this.router.navigate(['/']);
  }

  openConfirmModal() {
    this.modalService.open(this.content);
  }

  onSubmit() {
    if (this.privacyAccept && this.pecsMatch) {
      this.openConfirmModal();
    }
  }
}
