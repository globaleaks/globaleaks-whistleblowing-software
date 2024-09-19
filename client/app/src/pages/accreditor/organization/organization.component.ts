import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { ExternalOrganization,EOAdmin, EOPrimaryReceiver, EOUser, EOInfo } from '@app/models/accreditor/organization-data';
import { AccreditorOrgService } from '@app/services/helper/accreditor-org.service';
import { AuthenticationService } from '@app/services/helper/authentication.service';
import { HttpService } from '@app/shared/services/http.service';
import { map, Observable } from 'rxjs';
import { ConfirmationComponent } from '@app/shared/modals/confirmation/confirmation.component';

@Component({
  selector: 'src-organization',
  templateUrl: './organization.component.html'
})
export class OrganizationComponent implements OnInit{

  org_id: string | null;

  organization: ExternalOrganization;

  org_type: boolean = false;

  organizationInfo: EOInfo = {
    organization_name: '',
    organization_email: '',
    organization_institutional_site: ''
  };

  adminInfo: EOAdmin = {
    name: '',
    email: '',
    surname: '',
    fiscal_code: ''
  };

  receiverInfo: EOPrimaryReceiver = {
    name: '',
    surname: '',
    fiscal_code: '',
    email: ''
  };

  private actionHandlers: { [key: string]: () => void } = {
    'reload': () => this.loadOrganizationData(),
    'suspend': () => this.cambiaStatoOrganizzazioneAccreditata(),
    'reactivate': () => this.cambiaStatoOrganizzazioneAccreditata(),
    'update': () => this.aggiornaInfoOrganizazzione(),
    'delete': () => this.rifiuta()
  };

  constructor(private activatedRoute: ActivatedRoute, private httpService: HttpService,
    private orgService : AccreditorOrgService, private authenticationService: AuthenticationService,
    private modalService: NgbModal){

  }


  ngOnInit() {
   this.loadOrganizationData();

   const container = document.getElementById('actions-container');
    if (container) {
      container.addEventListener('click', this.onActionHandler.bind(this));
      container.addEventListener('keydown', this.onActionHandler.bind(this));
    }
  }

  loadOrganizationData(){
    console.log("LOAD ORGANIZATION DATA");
    this.org_id = this.activatedRoute.snapshot.paramMap.get("org_id");
    
    const requestObservable: Observable<ExternalOrganization> = this.httpService.accreditorAccreditationDetail(this.org_id);


    requestObservable.subscribe(
      {
        next: (response) => {
          this.orgService.reset();

          this.organization = response;
          
          this.organizationInfo.organization_email = response.organization_email
          this.organizationInfo.organization_name = response.organization_name
          this.organizationInfo.organization_institutional_site = response.organization_institutional_site

          this.adminInfo.name = response.admin_name
          this.adminInfo.surname = response.admin_surname
          this.adminInfo.fiscal_code = response.admin_fiscal_code
          this.adminInfo.email = response.admin_email

          this.receiverInfo.name = response.recipient_name
          this.receiverInfo.surname = response.recipient_surname
          this.receiverInfo.fiscal_code = response.recipient_fiscal_code
          this.receiverInfo.email = response.recipient_email

          console.log("response.state:", response.state);
          console.log("organization state:", this.organization.state);

          //todo mockup
          //this.org_type = this.organization.type === "AFFILIATED"

          //todo mockup:
          // let users : EOUser[] = [];
          // users.push({
          //   id: "zaoi1",
          //   creation_date: "01-01-2024",
          //   last_login: "01/02/2024 10:00:05",
          //   role: "RECIPIENT",
          //   opened_rtips: 10,
          //   closed_rtips: 1
          // },
          // {
          //   id: "abcde1",
          //   creation_date: "01-02-2024",
          //   last_login: "01/01/2024 10:00:05",
          //   role: "RECIPIENT",
          //   opened_rtips: 5,
          //   closed_rtips: 10
          // })

          // this.organization.users = users;

          //this.organization.state = "ACCREDITED";
          //fine mockup

        }
      });
  }
  
  convertiInAffiliata(){
    console.log("CONVERTI IN AFFILIATA - TODO!!!")
    if(this.org_type) // TODO richiesta info
      this.organization.type = "AFFILIATED"
  }

  invia(){
    //todo mockup
    //this.organization.state = "INVITED";
    //fine mockup
  
    console.log("INVIA / INVIA INVITO - TODO!!!");
    if (this.authenticationService.session.role === "accreditor") {
      this.httpService.sendAccreditationInvitation(this.organization.id).subscribe({
        next: () => {
          console.log("Invito inviato con successo");
          this.loadOrganizationData();
        },
        error: (err) => {
          console.error("Errore durante l'invio dell'invito", err);
        }
      }); 
    }
  }

  rifiuta(){
    //todo mockup
    // this.organization.state = "REJECTED";
    //fine mockup
    console.log("REJECT - TODO!!!")
    if (this.authenticationService.session.role === "accreditor") {
      const modalRef = this.modalService.open(ConfirmationComponent);

      modalRef.result.then((result) => {
        if (result) {
          this.httpService.deleteAccreditationRequest(this.organization.id).subscribe({
            next: () => {
              console.log("Richiesta rifiutata con successo");
              this.loadOrganizationData();
            },
            error: (err) => {
              console.error("Errore durante il rifiuto della richiesta", err);
            }
          });
        } else {
          console.log('Modal dismissed');
        }
      }).catch((error) => {
        console.log("Operazione annullata o chiusa", error);
      });
    }
  }

  onActionHandler(event: Event) {
    if (event instanceof MouseEvent || (event instanceof KeyboardEvent && event.key === 'Enter')) {
      const target = (event.target as HTMLElement).closest('span[data-action]');
      
      if (target) {
        const action = target.getAttribute('data-action');
        
        // Esegui l'azione corrispondente dalla mappa
        if (action && this.actionHandlers[action]) {
          this.actionHandlers[action]();
        }
      }
    }
  }

  cambiaStatoOrganizzazioneAccreditata() {
    //todo mockup
    // this.organization.state = "SUSPENDED"; //"SUSPENDED";
    //fine mockup
    console.log("CAMBIA STATO - TODO!!!")
    if (this.authenticationService.session.role === "accreditor") {
      this.httpService.toggleAccreditedOrganizationStatus(this.organization.id).subscribe({
        next: () => {
          console.log("Stato modificato con successo");
          this.loadOrganizationData();
        },
        error: (err) => {
          console.error("Errore durante il rifiuto della richiesta", err);
        }
      }); 
    }
  }

  aggiornaInfoOrganizazzione() {
    console.log("AGGIORNA DATI ORGANIZZAZIONE - TODO!!!")
    //todo mockup
    // this.organization.organization_name = "updated name";
    // this.organization.organization_email = "updated email";
    // this.organization.organization_institutional_site = "updated site";
    // this.organization.type = "NOT_AFFILIATED";
    //fine mockup
    if (this.authenticationService.session.role === "accreditor") {
      const updatedData = {
        organization_name: this.organizationInfo.organization_name,
        organization_email: this.organizationInfo.organization_email,
        organization_institutional_site: this.organizationInfo.organization_institutional_site,
        type: this.organization.type ? 'AFFILIATED' : 'NOT_AFFILIATED' as 'AFFILIATED' | 'NOT_AFFILIATED'
      };
      this.httpService.updateInfoAccreditedOrganizationRequest(this.organization.id, updatedData).subscribe({
        next: () => {
          console.log("Aggiornamento effettuato con successo");
          this.loadOrganizationData();
        },
        error: (err) => {
          console.error("Errore durante il rifiuto della richiesta", err);
        }
      }); 
    }
  }

  isRequested(){
    return this.organization.state === "requested"
  }

  isInstructorRequest(){
    return this.organization.state === "instructor_request"
  }

  isAccredited(){
    return this.organization.state === "accredited"
  }

  isSuspended(){
    return this.organization.state === "suspended"
  }

  isInvited(){
    return this.organization.state === "invited"
  }

  canDelete(){
    console.log("CAN DELETE");
    console.log(this.organization.opened_tips);
    console.log(this.organization.num_user_profiled);
    return this.organization.opened_tips == 0 && this.organization.num_user_profiled == 1;
  }

}
