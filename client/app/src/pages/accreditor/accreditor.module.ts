import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';

import {RouterModule} from "@angular/router";
import {SharedModule} from "@app/shared.module";
import {FormsModule} from "@angular/forms";
import {NgbModule, NgbNavModule} from "@ng-bootstrap/ng-bootstrap";
import { AccreditorHomeComponent } from './home/home.component';
import { SidebarComponent } from './sidebar/sidebar.component';
import { OrganizationsComponent } from './organizations/organizations.component';
import { OrganizationComponent } from './organization/organization.component';


@NgModule({
  declarations: [
    AccreditorHomeComponent, SidebarComponent, OrganizationsComponent, OrganizationComponent
  ],
  imports: [
    CommonModule, SharedModule, NgbNavModule, NgbModule, RouterModule, FormsModule
  ],
  exports: [SidebarComponent]
})
export class AccreditorModule { }
