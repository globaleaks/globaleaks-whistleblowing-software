import { Component } from '@angular/core';
import { Constants } from "@app/shared/constants/constants";
import {FormsModule} from '@angular/forms'

@Component({
  selector: 'src-org-info',
  templateUrl: './org-info.component.html'
})
export class OrgInfoComponent {

  protected readonly Constants = Constants;

  organizationInfo = {
    denomination: '',
    pec: '',
    confirmPec: '',
    institutionalWebsite: ''
  };

  pecsMatch = true;

  checkPecsMatch() {
    this.pecsMatch = this.organizationInfo.pec === this.organizationInfo.confirmPec;
  }

}
