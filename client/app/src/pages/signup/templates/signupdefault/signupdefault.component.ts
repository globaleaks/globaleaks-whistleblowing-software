import {Component, EventEmitter, Input, OnChanges, OnInit, Output, SimpleChanges, inject} from "@angular/core";
import {AppDataService} from "@app/app-data.service";
import {Signup} from "@app/models/component-model/signup";
import * as Constants from "@app/shared/constants/constants";
import {FormsModule} from "@angular/forms";
import {NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {NgClass} from "@angular/common";
import {SubdomainValidatorDirective} from "@app/shared/directive/subdomain-validator.directive";
import {DisableCcpDirective} from "@app/shared/directive/disable-ccp.directive";
import {TosComponent} from "../tos/tos.component";
import {TranslateModule} from "@ngx-translate/core";

@Component({
    selector: "src-signupdefault",
    templateUrl: "./signupdefault.component.html",
    standalone: true,
    imports: [FormsModule, NgbTooltipModule, NgClass, SubdomainValidatorDirective, DisableCcpDirective, TosComponent, TranslateModule]
})
export class SignupdefaultComponent implements OnInit, OnChanges {
  protected appDataService = inject(AppDataService);


  @Input() signup: Signup;
  @Input() idpRequired = false;
  @Input() idpAuthenticated = false;
  @Input() idpFields: { name: boolean, surname: boolean } = {name: false, surname: false};
  @Input() idpEmail = "";
  @Output() complete: EventEmitter<any> = new EventEmitter<any>();
  @Output() authenticate: EventEmitter<any> = new EventEmitter<any>();

  emailRegex: string;
  confirmation_email: string;
  confirmation_organization_email: string;
  validated = false;
  mail: string;
  subdomainEdited = false;

  ngOnInit(): void {
    this.emailRegex = Constants.Constants.emailRegexp;

    // A registration resumed after the round trip towards the identity provider
    // keeps the address chosen by the user in place of the computed one
    this.subdomainEdited = !!this.signup.subdomain && this.signup.subdomain !== this.computeSubdomain();

    // The confirmations are not kept across the round trip towards the
    // identity provider: the restored addresses were compiled by the user in
    // this same session, so they are not asked for a second time
    this.confirmation_email = this.signup.email;
    this.confirmation_organization_email = this.signup.organization_email;
  }

  ngOnChanges(changes: SimpleChanges): void {
    // The email published by the identity provider only prefills the form,
    // both in the field and in its confirmation: the user is free to correct
    // it and be notified on a different address
    if (changes["idpEmail"] && this.idpEmail && !this.signup.email) {
      this.signup.email = this.idpEmail;
      this.confirmation_email = this.idpEmail;
    }
  }

  // The address of the site is computed from the name of the organization and
  // stays in sync with it until the user edits it
  onOrganizationNameChange(): void {
    if (!this.subdomainEdited) {
      this.signup.subdomain = this.computeSubdomain();
    }
  }

  private computeSubdomain(): string {
    return (this.signup.organization_name || "").replace(/[^\w]/gi, "").toLowerCase().slice(0, 40);
  }

  get invitedSignup(): boolean {
    return !!this.signup.token;
  }

  get organizationRequested(): boolean {
    return !!this.appDataService.public.node.signup_request_organization;
  }

  // The site of an invited registration is the one created along the invitation
  get subdomainRequested(): boolean {
    return !!this.appDataService.public.node.signup_request_subdomain && !this.invitedSignup;
  }
}
