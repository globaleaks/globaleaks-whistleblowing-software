import { Component, Input, OnInit } from '@angular/core';
import { AccreditationRequestModel, OrganizationData } from '@app/models/accreditor/organization-data';

@Component({
  selector: 'src-org-overview',
  templateUrl: './org-overview.component.html'
})
export class OrgOverviewComponent implements OnInit {

  
  @Input() org: OrganizationData
  collapsed: boolean = false;


  ngOnInit(): void {
    
  }


  public toggleCollapse() {
    this.collapsed = !this.collapsed;
  }



}
