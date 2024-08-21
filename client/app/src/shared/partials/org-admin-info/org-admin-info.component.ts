import { Component } from '@angular/core';
import { Constants } from '@app/shared/constants/constants';

@Component({
  selector: 'src-org-admin-info',
  templateUrl: './org-admin-info.component.html'
})
export class OrgAdminInfoComponent {

  adminInfo = {
    name: '',
    email: '',
    fiscalCode: ''
  };

  protected readonly Constants = Constants;

}
