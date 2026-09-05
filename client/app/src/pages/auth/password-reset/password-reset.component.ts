import {Component, inject} from "@angular/core";
import {AppDataService} from "@app/app-data.service";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {UtilsService} from "@app/shared/services/utils.service";
import {NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {FormsModule} from "@angular/forms";
import {TranslateModule} from "@ngx-translate/core";

@Component({
    selector: "src-password-reset",
    templateUrl: "./password-reset.component.html",
    standalone: true,
    imports: [FormsModule, NgbTooltipModule, TranslateModule]
})
export class PasswordResetComponent {
  private readonly authenticationService = inject(AuthenticationService);
  protected utilsService = inject(UtilsService);
  protected appDataService = inject(AppDataService);

  username: string | undefined = undefined;

  submitRequest() {
    if (this.username !== undefined) {
      this.authenticationService.resetPassword(this.username);
    }
  }
}
