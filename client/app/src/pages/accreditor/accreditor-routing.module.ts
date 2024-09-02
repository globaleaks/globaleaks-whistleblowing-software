import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { AccreditorHomeComponent } from './home/home.component';
import { OrganizationsComponent } from './organizations/organizations.component';
import { AccreditationReqResolver } from '@app/shared/resolvers/accreditation-req-resolver.service';

const routes: Routes = [
  {
    path: "",
    component: AccreditorHomeComponent,
    pathMatch: "full",
    data: {sidebar: "accreditor-sidebar", pageTitle: "Home"},
  },
  {
    path: "home",
    component: AccreditorHomeComponent,
    pathMatch: "full",
    data: {sidebar: "accreditor-sidebar", pageTitle: "Home"},
  },
  {
    path: "organizations",
    component: OrganizationsComponent,
    resolve: {
      AccreditationReqResolver
    },
    pathMatch: "full",
    data: {sidebar: "accreditor-sidebar", pageTitle: "Organizations"},
  }


];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class AccreditorRoutingModule { }
