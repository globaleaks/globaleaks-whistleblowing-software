import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { OrganizationData } from '@app/models/accreditor/organization-data';
import { EOUser } from '@app/models/app/shared-public-model';
import { AccreditorOrgService } from '@app/services/helper/accreditor-org.service';
import { AuthenticationService } from '@app/services/helper/authentication.service';
import { HttpService } from '@app/shared/services/http.service';

@Component({
  selector: 'src-organization',
  templateUrl: './organization.component.html'
})
export class OrganizationComponent implements OnInit{

  org_id: string | null;
  loading: boolean = false;
  organization: OrganizationData;
  org_type: boolean = false;


  constructor(private activatedRoute: ActivatedRoute, private httpService: HttpService,
    private orgService : AccreditorOrgService, private authenticationService: AuthenticationService){

  }


  ngOnInit() {
   this.loadOrganizationData();
  }

  loadOrganizationData(){
    console.log("LOAD ORGANIZATION DATA");
    this.org_id = this.activatedRoute.snapshot.paramMap.get("org_id");
    
    // const requestObservable: Observable<any> = this.httpService.receiverTip(this.org_id);
    this.loading = true;
    this.orgService.reset();

    // setTimeout(()=>{
      this.organization = new OrganizationData();
      this.organization.id = "1"
      this.organization.denomination = "denominazione Org 1"
      this.organization.accreditation_date = "01-02-2024"
      this.organization.num_tip = 10
      this.organization.num_user_profiled = 2
      this.organization.type = "NOT_AFFILIATED"
      // •	0 -> REQUESTED
      // •	1 -> ACCREDITED
      // •	2 -> REJECTED
      // •	3 -> INSTRUCTOR_REQUEST
      // •	4 -> INVITED
      // •	5 -> SUSPEND
      // •	6 -> APPROVED
      this.organization.state = "ACCREDITED"
      
      let users : EOUser[] = [];
      users.push({
        id: "1",
        name: "Utente 1",
        surname: "Surname 1",
        creation_date: "01-01-2024",
        last_access: "01/02/2024 10:00:05",
        role: "Admin",
        tips: 10,
        closed_tips: 1
      })

      this.organization.users = users;
    
    
    // }, 1000)

    // requestObservable.subscribe(
    //   {
    //     next: (response: OrganizationData) => {
    //       this.loading = false;
    //       this.organization = this.orgService.organization;

    //       // this.activatedRoute.queryParams.subscribe((params: { [x: string]: string; }) => {
    //       //   this.tip.tip_id = params["tip_id"];
    //       // })

    //       //TODO: CHIAMATA PER RECUPERARE LISTA UTENTI DELL'ORGANIZZAZIONE
    //       // this.httpService.getOrgUsers(this.org_id)
          
    //     }
    //   }
    // );
  }

  
  convertiInAffiliata(){
    console.log("CONVERTI IN AFFILIATA - TODO!!!")
  }

  invia(){
    if(this.org_type) // TODO richiesta info
      this.organization.type = "AFFILIATED"
  
    console.log("INVIA / INVIA INVITO - TODO!!!", this.organization.id);
    // if (this.authenticationService.session.role === "accreditor") {
    //   this.httpService.sendAccreditationInvitation(this.organization.id).subscribe({
    //     next: (response) => {
    //       console.log("Invito inviato con successo", response);
    //       this.loadOrganizationData();
    //     },
    //     error: (err) => {
    //       console.error("Errore durante l'invio dell'invito", err);
    //     }
    //   }); 
    // }
  }

  rifiuta(){
    console.log("REJECT - TODO!!!")
    // if (this.authenticationService.session.role === "accreditor") {
    //   this.httpService.deleteAccreditationRequest(this.organization.id).subscribe({
    //     next: (response) => {
    //       console.log("Richiesta rifiutata con successo", response);
    //       this.loadOrganizationData();
    //     },
    //     error: (err) => {
    //       console.error("Errore durante il rifiuto della richiesta", err);
    //     }
    //   }); 
    // }

  }

      // •	0 -> REQUESTED
      // •	1 -> ACCREDITED
      // •	2 -> REJECTED
      // •	3 -> INSTRUCTOR_REQUEST
      // •	4 -> INVITED
      // •	5 -> SUSPEND

  isRequested(){
    return this.organization.state === "REQUESTED"
  }

  isInstructorRequest(){
    return this.organization.state === "INSTRUCTOR_REQUEST"
  }

  isAccredited(){
    return this.organization.state === "ACCREDITED"
  }

  isSuspended(){
    return this.organization.state === "SUSPENDED"
  }

  isInvited(){
    return this.organization.state === "INVITED"
  }

}
