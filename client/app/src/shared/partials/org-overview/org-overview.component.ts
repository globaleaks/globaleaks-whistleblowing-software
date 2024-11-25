import { Component, Input } from '@angular/core';
import { ExternalOrganization } from '@app/models/accreditor/organization-data';

@Component({
  selector: 'src-org-overview',
  templateUrl: './org-overview.component.html'
})
export class OrgOverviewComponent {

  
  @Input() org: ExternalOrganization
  collapsed: boolean = false;



  public toggleCollapse() {
    this.collapsed = !this.collapsed;
  }



}
