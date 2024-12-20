import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { ExternalOrganization,EOAdmin, EOPrimaryReceiver, EOInfo } from '@app/models/accreditor/organization-data';
import { AccreditorOrgService } from '@app/services/helper/accreditor-org.service';
import { AuthenticationService } from '@app/services/helper/authentication.service';
import { HttpService } from '@app/shared/services/http.service';
import { Observable } from 'rxjs';
import { CustomModalComponent } from '@app/shared/modals/custom-modal/custom-modal.component';
import { TranslateService } from '@ngx-translate/core';

@Component({
  selector: 'src-organization',
  templateUrl: './organization.component.html'
})
export class OrganizationComponent implements OnInit{

  org_id: string | null;
  organization: ExternalOrganization;
  isChecked: boolean = false;
  isFormValid: boolean = true;

  organizationInfo: EOInfo = {
    organization_name: '',
    organization_email: '',
    organization_institutional_site: ''
  };

  adminInfo: EOAdmin = {
    admin_name: '',
    admin_email: '',
    admin_surname: '',
    idp_id: ''
  };

  receiverInfo: EOPrimaryReceiver = {
    name: '',
    surname: '',
    idp_id: '',
    email: ''
  };

  private readonly actionHandlers: { [key: string]: () => void } = {
    'reload': () => this.loadOrganizationData(),
    'suspend': () => this.sospendiAttivaOrganizzazioneAccreditata("suspend"),
    'reactivate': () => this.sospendiAttivaOrganizzazioneAccreditata("reactivate"),
    'delete': () => this.rifiuta()
  };

  constructor(private readonly activatedRoute: ActivatedRoute, private readonly httpService: HttpService,
    private readonly orgService : AccreditorOrgService, private readonly authenticationService: AuthenticationService,
    private readonly modalService: NgbModal, private readonly router: Router, private readonly translateService: TranslateService){

  }

  ngOnInit() {
   this.loadOrganizationData();
  }

  loadOrganizationData(){
    this.org_id = this.activatedRoute.snapshot.paramMap.get("org_id");    
    const requestObservable: Observable<ExternalOrganization> = this.httpService.accreditorAccreditationDetail(this.org_id);

    requestObservable.subscribe(
      {
        next: (response) => {
          this.orgService.reset();

          this.organization = response;
          
          this.organizationInfo.organization_email = response.organization_email;
          this.organizationInfo.organization_name = response.organization_name;
          this.organizationInfo.organization_institutional_site = response.organization_institutional_site;

          this.adminInfo.admin_name = response.admin_name;
          this.adminInfo.admin_surname = response.admin_surname;
          this.adminInfo.idp_id = response.admin_tax_code;
          this.adminInfo.admin_email = response.admin_email;

          this.receiverInfo.name = response.recipient_name;
          this.receiverInfo.surname = response.recipient_surname;
          this.receiverInfo.idp_id = response.recipient_tax_code;
          this.receiverInfo.email = response.recipient_email;

          const container = document.getElementById('actions-container');
          if (container) {
              container.addEventListener('click', this.onActionHandler.bind(this));
              container.addEventListener('keydown', this.onActionHandler.bind(this));
          }
         
          this.isAffiliated();

        },
        error: (err) => {
            console.error("Errore nel caricamento dei dati dell'organizzazione: ", err);
        }
      });
  }

  invia(){  
    if (this.authenticationService.session.role === "accreditor") {
      if (this.isOrganizationDataChanged(this.organizationInfo)) {
        this.aggiornaDatiOrganizazzione();
      }

      if(this.organization.state === 'instructor_request' || this.organization.state === 'invited'){
        this.httpService.sendAccreditationInvitation(this.organization.id).subscribe({
          next: () => {
            this.loadOrganizationData();
          },
          error: (err) => {
            console.error("Errore durante l'invio dell'invito", err);
          }
        }); 
      }
      else if(this.organization.state === 'requested'){
        this.httpService.sendAccreditationApproved(this.organization.id).subscribe({
          next: () => {
            this.loadOrganizationData();
          },
          error: (err) => {
            console.error("Errore durante l'invio dell'invito", err);
          }
        });
      }      
    }
  }

  rifiuta(){
    if (this.authenticationService.session.role === "accreditor") {
      const modalRef = this.modalService.open(CustomModalComponent);
      modalRef.componentInstance.title = this.translateService.instant("Do you confirm the operation?");
      modalRef.componentInstance.message = this.translateService.instant("Insert here the reason of the operation:");
      modalRef.componentInstance.arg = this.organization.id;
      modalRef.componentInstance.showInputText = true;

      modalRef.componentInstance.confirmFunction = (arg: string, text: string) => {
        this.httpService.deleteAccreditationRequest(arg, {'motivation_text': text}).subscribe({
          next: () => {
            this.router.navigateByUrl('/accreditor/organizations');
          },
          error: (err) => {
            console.error("Errore durante il rifiuto della richiesta", err);
          }
        });
      };
    }
  }

  onActionHandler(event: Event) {
    if (event instanceof MouseEvent || (event instanceof KeyboardEvent && event.key === 'Enter')) {
      const target = (event.target as HTMLElement).closest('span[data-action]');
      
      if (target) {
        const action = target.getAttribute('data-action');
        
        if (action && this.actionHandlers[action]) {
          this.actionHandlers[action]();
        }
      }
    }
  }

  sospendiAttivaOrganizzazioneAccreditata(action: 'suspend' | 'reactivate') {
    if (this.authenticationService.session.role === "accreditor") {
      const modalRef = this.modalService.open(CustomModalComponent);
      modalRef.componentInstance.title = action === 'suspend' ? this.translateService.instant("Confirm suspension") : this.translateService.instant("Confirm reactivation");
      modalRef.componentInstance.message = this.translateService.instant("Confirm message suspension/reactivation");
      modalRef.componentInstance.showInputText = false;

      modalRef.componentInstance.confirmFunction = () => {
        this.httpService.toggleAccreditedOrganizationStatus(this.organization.id).subscribe({
          next: () => {
            this.loadOrganizationData();
          },
          error: (err) => {
            console.error("Errore durante il rifiuto della richiesta", err);
          }
        }); 
      };      
    }
  }

  aggiornaStatoAffiliazioneOrganizazzione() {
    const updatedData = {
      organization_name: this.organizationInfo.organization_name,
      organization_email: this.organizationInfo.organization_email,
      organization_institutional_site: this.organizationInfo.organization_institutional_site,
      type: this.organization.type === 'AFFILIATED' ? 'NOT_AFFILIATED' : 'AFFILIATED' as 'AFFILIATED' | 'NOT_AFFILIATED'
    };
    this.inviaAggiornamentoOrganizzazione(updatedData);
  }

  aggiornaDatiOrganizazzione() {
    const updatedData = {
      organization_name: this.organizationInfo.organization_name,
      organization_email: this.organizationInfo.organization_email,
      organization_institutional_site: this.organizationInfo.organization_institutional_site
    };
    this.inviaAggiornamentoOrganizzazione(updatedData);
  }

  private inviaAggiornamentoOrganizzazione(updatedData: { 
    organization_name?: string, organization_email?: string,
    organization_institutional_site?: string, type?: 'AFFILIATED' | 'NOT_AFFILIATED' }) {
      if (this.authenticationService.session.role === "accreditor") {
        this.httpService.updateOrganizationInfoRequest(this.organization.id, updatedData).subscribe({
          next: () => {
            this.loadOrganizationData();
          },
          error: (err) => {
            console.error("Errore durante la richiesta di aggiornamento", err);
          }
        });
      }
  }

  private isOrganizationDataChanged(updatedData: {
    organization_name?: string, organization_email?: string,
    organization_institutional_site?: string }): boolean {
      return (
        updatedData.organization_name !== this.organization.organization_name ||
        updatedData.organization_email !== this.organization.organization_email ||
        updatedData.organization_institutional_site !== this.organization.organization_institutional_site
      );
  }

  isState(state: string): boolean {
    return this.organization?.state === state;
  }

  canDelete(){
    return this.organization?.opened_tips == 0 && this.organization.num_user_profiled == 2;
  }

  isAffiliated(){
    this.isChecked = this.organization?.type === "AFFILIATED";
    return this.isChecked
  }

  onFormValidityChange(isValid: boolean) {
    this.isFormValid = isValid;
  }

}
