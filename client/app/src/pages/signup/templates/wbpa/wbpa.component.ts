import {Component, inject, output, input} from "@angular/core";
import * as Constants from "@app/shared/constants/constants";
import {AppDataService} from "@app/app-data.service";
import {Signup} from "@app/models/component-model/signup";
import {FormsModule} from "@angular/forms";
import {NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {DisableCcpDirective} from "@app/shared/directive/disable-ccp.directive";
import {SubdomainValidatorDirective} from "@app/shared/directive/subdomain-validator.directive";
import {TosComponent} from "../tos/tos.component";
import {TranslateModule} from "@ngx-translate/core";
import {TranslatorPipe} from "@app/shared/pipes/translate";

@Component({
    selector: "src-wbpa",
    templateUrl: "./wbpa.component.html",
    standalone: true,
    imports: [FormsModule, NgbTooltipModule, DisableCcpDirective, SubdomainValidatorDirective, TosComponent, TranslateModule, TranslatorPipe]
})
export class WbpaComponent {
  protected appDataService = inject(AppDataService);

  readonly signup = input.required<Signup>();
  readonly complete = output<void>();
  readonly updateSubdomain = output<void>();

  protected readonly Constants = Constants;
  validated = false;
  confirmation_email: string;
}
