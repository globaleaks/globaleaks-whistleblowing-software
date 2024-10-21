import {Component, EventEmitter, Input, OnInit, Output, inject} from "@angular/core";
import {AppDataService} from "@app/app-data.service";
import {Signup} from "@app/models/component-model/signup";
import * as Constants from "@app/shared/constants/constants";
import {FormsModule} from "@angular/forms";
import {NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {NgClass} from "@angular/common";
import {SubdomainValidatorDirective} from "../../../../shared/directive/subdomain-validator.directive";
import {DisableCcpDirective} from "../../../../shared/directive/disable-ccp.directive";
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
  @Output() complete: EventEmitter<any> = new EventEmitter<any>();

  emailRegex: string;
  confirmation_email: string;
  validated = false;
  mail: string;

  ngOnInit(): void {
    this.emailRegex = Constants.Constants.emailRegexp;
  }
}
