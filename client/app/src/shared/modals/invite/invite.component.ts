import {ChangeDetectorRef, Component, OnInit, inject} from "@angular/core";
import {NgbActiveModal} from "@ng-bootstrap/ng-bootstrap";
import {TranslateModule} from "@ngx-translate/core";
import {FormsModule} from "@angular/forms";
import {HttpService} from "@app/shared/services/http.service";
import {Constants} from "@app/shared/constants/constants";

@Component({
  selector: 'src-invite',
  templateUrl: './invite.component.html',
  standalone: true,
  imports: [FormsModule, TranslateModule],
})
export class InviteComponent implements OnInit {
  private activeModal = inject(NgbActiveModal);
  private httpService = inject(HttpService);
  private cdr = inject(ChangeDetectorRef);
  protected readonly Constants = Constants;

  invite = {
    organization_name: '',
    email: '',
    mail_template: ''
  };

  confirmFunction: (invite: {organization_name: string, email: string, mail_template: string}) => void;

  ngOnInit(): void {
    this.httpService.requestNotificationsResource().subscribe(notification => {
      this.invite.mail_template = notification.signup_invite_mail_template;
      // The response lands outside change detection (zoneless): request a
      // refresh so the prefilled template is rendered.
      this.cdr.markForCheck();
    });
  }

  confirm() {
    this.confirmFunction(this.invite);
    return this.activeModal.close();
  }

  cancel() {
    this.activeModal.dismiss();
  }
}
