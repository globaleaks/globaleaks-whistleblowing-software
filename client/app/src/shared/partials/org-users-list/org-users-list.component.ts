import { Component, Input } from '@angular/core';
import { EOUser } from '@app/models/accreditor/organization-data';

@Component({
  selector: 'src-org-users-list',
  templateUrl: './org-users-list.component.html'
})
export class OrgUsersListComponent {

  @Input() users: EOUser[];
  collapsed: boolean = false;
  sortKey: string = "creation_date";
  sortReverse: boolean = true;

  public toggleCollapse() {
    this.collapsed = !this.collapsed;
  }


  orderbyCast(data: EOUser[]): EOUser[] {
    return data;
  }

}
