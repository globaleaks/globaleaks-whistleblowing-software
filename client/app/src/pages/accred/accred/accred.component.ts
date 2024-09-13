import { Component, ViewChild, TemplateRef } from "@angular/core";
import { Constants } from "@app/shared/constants/constants";
import { ActivatedRoute, Router } from "@angular/router";
import { AppDataService } from "@app/app-data.service";
import { NgbModal } from "@ng-bootstrap/ng-bootstrap";
import { NgForm } from "@angular/forms";
import { AccreditationSubscriberModel } from "@app/models/resolvers/accreditation-model";
import { EOAdmin, EOPrimaryReceiver, ExternalOrganization } from "@app/models/app/shared-public-model";
import { UtilsService } from "@app/shared/services/utils.service";

@Component({
  selector: "app-login",
  templateUrl: "./accred.component.html"
})
export class AccredComponent {
  @ViewChild("accredForm") public accredForm: NgForm;
  @ViewChild('content') content: TemplateRef<any>;
  modalMessage = 'A confirmation email will be sent to the organization\'s PEC.';

  protected readonly location = location;
  protected readonly Constants = Constants;

  pecConfirmed: string;

  organizationInfo: ExternalOrganization = {
    denomination: '',
    pec: '',
    institutional_site: ''
  };

  adminInfo: EOAdmin = {
    name: '',
    email: '',
    surname: ''
  };

  receiverInfo: EOPrimaryReceiver = {
    name: '',
    surname: '',
    fiscal_code: '',
    email: ''
  };

  pecsMatch = true;
  privacyAccept = false;
  privacyPolicy = 'Your privacy policy text here...';

  constructor(public router: Router, private route: ActivatedRoute, protected appDataService: AppDataService, private modalService: NgbModal, private utilsService: UtilsService) {}

  checkPecsMatch() {
    this.pecsMatch = this.organizationInfo.pec === this.pecConfirmed;
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
      this.utilsService.submitAccreditationRequest(this.buildAccreditationRequest()).subscribe(_ => {
        this.openConfirmModal();
      });
    }
  }



  buildAccreditationRequest() : AccreditationSubscriberModel{

    let request: AccreditationSubscriberModel = new AccreditationSubscriberModel();

    request.admin_email = this.adminInfo.email
    request.admin_name = this.adminInfo.name
    request.admin_surname = this.adminInfo.surname

    request.organization_email = this.organizationInfo.pec
    request.organization_name = this.organizationInfo.denomination
    request.organization_institutional_site = this.organizationInfo.institutional_site

    request.name = this.receiverInfo.name
    request.surname = this.receiverInfo.surname
    request.email = this.receiverInfo.email
    request.recipient_fiscal_code = this.receiverInfo.fiscal_code

    request.tos1 = true;
    request.tos2 = false;

    return request;
 
  }
}
