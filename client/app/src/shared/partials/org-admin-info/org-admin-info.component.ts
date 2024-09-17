import { Component, Input } from '@angular/core';
import { EOAdmin } from '@app/models/accreditor/organization-data';
import { Constants } from '@app/shared/constants/constants';

@Component({
  selector: 'src-org-admin-info',
  templateUrl: './org-admin-info.component.html'
})
export class OrgAdminInfoComponent {

  @Input() visualization: boolean = true;

  @Input() adminInfo: EOAdmin;

  protected readonly Constants = Constants;

}
