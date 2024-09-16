import { Component, Input } from '@angular/core';
import { EOInfo } from '@app/models/accreditor/organization-data';
import { Constants } from "@app/shared/constants/constants";

@Component({
  selector: 'src-org-info',
  templateUrl: './org-info.component.html'
})
export class OrgInfoComponent {

  protected readonly Constants = Constants;

  @Input() orgInfo: EOInfo;
  @Input() visualization: boolean = true;


}
