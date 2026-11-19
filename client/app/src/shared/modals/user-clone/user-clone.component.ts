import {Component, inject} from "@angular/core";
import {FormsModule} from "@angular/forms";
import {NgbActiveModal, NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {TranslatePipe} from "@ngx-translate/core";
import {User} from "@app/models/resolvers/user-resolver-model";
import {Constants} from "@app/shared/constants/constants";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {PreferenceResolver} from "@app/shared/resolvers/preference.resolver";
import {HttpService} from "@app/shared/services/http.service";

/**
 * Creation of a user as a clone of another one: the server gives the clone the role,
 * the permissions, the channels and the questionnaire triggers of the user it is made
 * from and, on request, access to its reports. The keys of the reports can be handed
 * to the clone only through the key escrow, so the option stays on No for an
 * administrator without access to it.
 */
@Component({
  selector: "src-user-clone",
  templateUrl: "./user-clone.component.html",
  standalone: true,
  imports: [FormsModule, NgbTooltipModule, TranslatePipe]
})
export class UserCloneComponent {
  private readonly activeModal = inject(NgbActiveModal);
  private readonly httpService = inject(HttpService);
  protected readonly nodeResolver = inject(NodeResolver);
  private readonly preferenceResolver = inject(PreferenceResolver);

  user: User;
  clone = {username: "", name: "", email: "", send_activation_link: true, reports: false};
  protected readonly Constants = Constants;

  get canGrantReports(): boolean {
    return !!this.preferenceResolver.dataModel?.escrow;
  }

  confirm(): void {
    this.httpService.requestCloneAdminUser({
      user_id: this.user.id,
      username: this.clone.username,
      name: this.clone.name,
      mail_address: this.clone.email,
      send_activation_link: this.clone.send_activation_link,
      reports: this.canGrantReports && this.clone.reports
    }).subscribe(() => {
      this.activeModal.close();
    });
  }

  cancel(): void {
    this.activeModal.dismiss();
  }
}
