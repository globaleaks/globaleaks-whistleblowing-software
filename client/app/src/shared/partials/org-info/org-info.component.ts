import { Component, Input } from '@angular/core';
import { Constants } from "@app/shared/constants/constants";
import { ExternalOrganization } from '@app/models/app/shared-public-model';

@Component({
  selector: 'src-org-info',
  templateUrl: './org-info.component.html'
})
export class OrgInfoComponent {

  protected readonly Constants = Constants;

  @Input() orgInfo: ExternalOrganization;
  @Input() visualization: boolean = true;


}
