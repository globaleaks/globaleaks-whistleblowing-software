import { Component, EventEmitter, Input, Output, inject } from "@angular/core";
import * as Constants from "@app/shared/constants/constants";
import {AppDataService} from "@app/app-data.service";
import {Signup} from "@app/models/component-model/signup";
import { FormsModule } from "@angular/forms";
import { NgClass } from "@angular/common";
import { DisableCcpDirective } from "../../../../shared/directive/disable-ccp.directive";
import { SubdomainValidatorDirective } from "../../../../shared/directive/subdomain-validator.directive";
import { TosComponent } from "../tos/tos.component";
import { TranslateModule } from "@ngx-translate/core";
import { TranslatorPipe } from "@app/shared/pipes/translate";

@Component({
    selector: "src-wbpa",
    templateUrl: "./wbpa.component.html",
    standalone: true,
    imports: [FormsModule, NgClass, DisableCcpDirective, SubdomainValidatorDirective, TosComponent, TranslateModule, TranslatorPipe]
})
export class WbpaComponent {
  protected appDataService = inject(AppDataService);

  @Input() signup: Signup;
  @Output() complete: EventEmitter<any> = new EventEmitter<any>();
  @Output() updateSubdomain: EventEmitter<any> = new EventEmitter<any>();

  protected readonly Constants = Constants;
  validated = false;
  confirmation_email: string;
}
