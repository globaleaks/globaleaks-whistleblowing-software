import { Component, ViewChild, TemplateRef, OnInit } from "@angular/core";
import { Constants } from "@app/shared/constants/constants";
import { ActivatedRoute, Router } from "@angular/router";
import { AppDataService } from "@app/app-data.service";
import { NgbModal } from "@ng-bootstrap/ng-bootstrap";
import { NgForm } from "@angular/forms";
import { AccreditationSubscriberModel } from "@app/models/resolvers/accreditation-model";
import { UtilsService } from "@app/shared/services/utils.service";
import { EOAdmin, EOInfo, EOPrimaryReceiver, ExternalOrganization } from "@app/models/accreditor/organization-data";
import { HttpService } from "@app/shared/services/http.service";
import { Observable } from "rxjs";

@Component({
  selector: "app-login",
  templateUrl: "./accred.component.html"
})
export class AccredComponent implements OnInit{
  @ViewChild("accredForm") public accredForm: NgForm;
  @ViewChild('content') content: TemplateRef<any>;
  modalMessage = 'A confirmation email will be sent to the organization\'s PEC.';

  protected readonly location = location;
  protected readonly Constants = Constants;

  pecConfirmed: string;

  organizationInfo: EOInfo = {
    organization_name: '',
    organization_email: '',
    organization_institutional_site: ''
  };

  adminInfo: EOAdmin = {
    admin_name: '',
    admin_email: '',
    admin_surname: '',
    idp_id: ""
  };

  receiverInfo: EOPrimaryReceiver = {
    name: '',
    surname: '',
    idp_id: '',
    email: ''
  };

  pecsMatch = true;
  privacyAccept = false;
  org_id: string | null;
  readOnly: boolean = false;
  state: string | null;
  

  constructor(public router: Router, private activatedRoute: ActivatedRoute, protected appDataService: AppDataService, private modalService: NgbModal, private utilsService: UtilsService, private httpService: HttpService) {}
  
  
  ngOnInit(): void {

    this.org_id = this.activatedRoute.snapshot.paramMap.get("org_id");

    if(this.org_id)
      this.loadOrganizationData();

  }

  loadOrganizationData(){

      const requestObservable: Observable<ExternalOrganization> = this.httpService.accreditorAccreditationDetail(this.org_id);

      requestObservable.subscribe(
        {
          next: (response) => {

            this.state = response.state;

            if(this.state !== "invited")
              this.readOnly =  true;
            
            this.organizationInfo.organization_email = response.organization_email
            this.organizationInfo.organization_name = response.organization_name
            this.organizationInfo.organization_institutional_site = response.organization_institutional_site

            this.adminInfo.admin_name = response.admin_name
            this.adminInfo.admin_surname = response.admin_surname
            this.adminInfo.admin_email = response.admin_email

            this.receiverInfo.name = response.recipient_name
            this.receiverInfo.surname = response.recipient_surname
            this.receiverInfo.idp_id = response.recipient_tax_code
            this.receiverInfo.email = response.recipient_email

          }
        }
      );

  }


  checkPecsMatch() {
    this.pecsMatch = this.organizationInfo.organization_email === this.pecConfirmed;
  }

  closeModal(modal: any) {
    modal.close('Close click');

    if(this.appDataService.public.proxy_idp_enabled)
      window.location.href="/logout"
  }

  openConfirmModal() {
    this.modalService.open(this.content);
  }

  onSubmit() {
    if (this.privacyAccept && this.pecsMatch) {
      if(!this.org_id)
        this.utilsService.submitAccreditationRequest(this.buildAccreditationRequest()).subscribe(_ => {
          this.openConfirmModal();
        });
      else if (this.state==="invited"){
        this.utilsService.submitAccreditationRequestFromInvitation(this.org_id, this.buildAccreditationRequest()).subscribe(_ => {
          this.openConfirmModal();
        });
      }
      else
        this.httpService.requestUpdateEOAccredited(this.org_id, {tos2: this.privacyAccept}).subscribe(_=> {
          this.openConfirmModal();
      })
    }
  }



  buildAccreditationRequest() : AccreditationSubscriberModel{

    let request: AccreditationSubscriberModel = new AccreditationSubscriberModel();

    request.admin_email = this.adminInfo.admin_email
    request.admin_name = this.adminInfo.admin_name
    request.admin_surname = this.adminInfo.admin_surname

    request.organization_email = this.organizationInfo.organization_email
    request.organization_name = this.organizationInfo.organization_name
    request.organization_institutional_site = this.organizationInfo.organization_institutional_site

    request.recipient_name = this.receiverInfo.name
    request.recipient_surname = this.receiverInfo.surname
    request.recipient_email = this.receiverInfo.email
    request.recipient_tax_code = this.receiverInfo.idp_id

    request.tos1 = this.privacyAccept;
    request.tos2 = false;

    return request;
 
  }
}
