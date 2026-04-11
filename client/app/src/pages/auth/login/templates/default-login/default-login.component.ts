import {Component, Input, inject} from "@angular/core";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {LoginDataRef} from "@app/pages/auth/login/model/login-model";
import {UtilsService} from "@app/shared/services/utils.service";
import {ControlContainer, NgForm, FormsModule} from "@angular/forms";
import {NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {TranslateModule} from "@ngx-translate/core";
import {TranslatorPipe} from "@app/shared/pipes/translate";

@Component({
    selector: "app-default-login",
    templateUrl: "./default-login.component.html",
    viewProviders: [{ provide: ControlContainer, useExisting: NgForm }],
    standalone: true,
    imports: [
    FormsModule,
    NgbTooltipModule,
    TranslateModule,
    TranslatorPipe
],
})
export class DefaultLoginComponent {
  protected utilsService = inject(UtilsService);
  protected authentication = inject(AuthenticationService);

  @Input() loginData: LoginDataRef;
  @Input() loginValidator: NgForm;
}
