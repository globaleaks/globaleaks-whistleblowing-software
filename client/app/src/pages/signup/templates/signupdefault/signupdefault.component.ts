import {Component, EventEmitter, Input, OnInit, Output, inject} from "@angular/core";
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
import {TranslatorPipe} from "@app/shared/pipes/translate";

@Component({
    selector: "src-signupdefault",
    templateUrl: "./signupdefault.component.html",
    standalone: true,
    imports: [FormsModule, NgbTooltipModule, NgClass, SubdomainValidatorDirective, DisableCcpDirective, TosComponent, TranslateModule, TranslatorPipe]
})
export class SignupdefaultComponent implements OnInit {
  protected appDataService = inject(AppDataService);


  @Input() signup: Signup;
  @Input() idpRequired = false;
  @Input() idpAuthenticated = false;
  @Input() idpFields: { name: boolean, surname: boolean, email: boolean } = {name: false, surname: false, email: false};
  @Output() complete: EventEmitter<any> = new EventEmitter<any>();
  @Output() authenticate: EventEmitter<any> = new EventEmitter<any>();

  emailRegex: string;
  confirmation_email: string;
  confirmation_organization_email: string;
  validated = false;
  mail: string;

  ngOnInit(): void {
    this.emailRegex = Constants.Constants.emailRegexp;
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
