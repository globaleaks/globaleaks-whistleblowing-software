import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { AccreditorHomeComponent } from './home/home.component';
import { OrganizationsComponent } from './organizations/organizations.component';
import { AccreditationReqResolver } from '@app/shared/resolvers/accreditation-req-resolver.service';
import { NodeResolver } from '@app/shared/resolvers/node.resolver';
import { PreferencesComponent } from '@app/shared/partials/preferences/preferences.component';
import { PreferenceResolver } from '@app/shared/resolvers/preference.resolver';
import { RTipsResolver } from '@app/shared/resolvers/r-tips-resolver.service';

const routes: Routes = [
  {
    path: "",
    component: AccreditorHomeComponent,
    pathMatch: "full",
    resolve: {
      AccreditationReqResolver, PreferenceResolver
    },
    data: {pageTitle: "Home"},
  },
  {
    path: "home",
    component: AccreditorHomeComponent,
    pathMatch: "full",
    resolve: {
      AccreditationReqResolver, PreferenceResolver
    },
    data: { pageTitle: "Home"},
  },
  {
    path: "organizations",
    component: OrganizationsComponent,
    resolve: {
      AccreditationReqResolver
    },
    pathMatch: "full",
    data: {pageTitle: "Organizations"},
  },
  {
    path: "preferences",
    component: PreferencesComponent,
    pathMatch: "full",
    resolve: {
      PreferenceResolver, RTipsResolver
    },
    data: {pageTitle: "Preferences"},
  }

];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class AccreditorRoutingModule { }
