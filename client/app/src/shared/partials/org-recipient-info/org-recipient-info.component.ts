import { Component, Input } from '@angular/core';
import { EOPrimaryReceiver } from '@app/models/accreditor/organization-data';
import { Constants } from '@app/shared/constants/constants';

@Component({
  selector: 'src-org-recipient-info',
  templateUrl: './org-recipient-info.component.html'
})
export class OrgRecipientInfoComponent {

  @Input() recipientInfo: EOPrimaryReceiver;
  @Input() visualization: boolean = true;

  
  protected readonly Constants = Constants;
}
