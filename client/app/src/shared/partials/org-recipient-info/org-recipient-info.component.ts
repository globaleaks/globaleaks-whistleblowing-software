import { Component } from '@angular/core';
import { Constants } from '@app/shared/constants/constants';

@Component({
  selector: 'src-org-recipient-info',
  templateUrl: './org-recipient-info.component.html'
})
export class OrgRecipientInfoComponent {

  recipientInfo = {
    name: '',
    fiscalCode: '',
    email: ''
  };

  protected readonly Constants = Constants;
}
