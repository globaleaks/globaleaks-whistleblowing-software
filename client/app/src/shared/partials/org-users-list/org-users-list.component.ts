import { Component, OnInit } from '@angular/core';
import { EOUser } from '@app/models/app/shared-public-model';

@Component({
  selector: 'src-org-users-list',
  templateUrl: './org-users-list.component.html'
})
export class OrgUsersListComponent implements OnInit {

  ngOnInit(): void {
    
  }

  collapsed: boolean = false;
  users: EOUser[] = [];
  sortKey: string = "creation_date";
  sortReverse: boolean = true;

  public toggleCollapse() {
    this.collapsed = !this.collapsed;
  }


}
