import {Component, inject, input} from "@angular/core";
import {AppDataService} from "@app/app-data.service";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {LoginDataRef} from "@app/pages/auth/login/model/login-model";
import {UtilsService} from "@app/shared/services/utils.service";
import {ControlContainer, NgForm, FormsModule} from "@angular/forms";
import {NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {TranslateModule} from "@ngx-translate/core";

@Component({
    selector: "app-default-login",
    templateUrl: "./default-login.component.html",
    viewProviders: [{ provide: ControlContainer, useExisting: NgForm }],
    standalone: true,
    imports: [
    FormsModule,
    NgbTooltipModule,
    TranslateModule
],
})
export class DefaultLoginComponent {
  protected utilsService = inject(UtilsService);
  protected authentication = inject(AuthenticationService);
  protected appDataService = inject(AppDataService);

  readonly loginData = input<LoginDataRef>();
  readonly loginValidator = input.required<NgForm>();
}
