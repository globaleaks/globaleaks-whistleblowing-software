import {Routes} from "@angular/router";
import {PreferenceResolver} from "@app/shared/resolvers/preference.resolver";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {RTipsResolver} from "@app/shared/resolvers/r-tips-resolver.service";
import {IarResolver} from "@app/shared/resolvers/iar-resolver.service";

export const custodianRoutes: Routes = [
  {
    path: "preferences",
    loadComponent: () => import('@app/shared/partials/preferences/preferences.component').then(m => m.PreferencesComponent),
    pathMatch: "full",
    data: {pageTitle: "Preferences"},
  },
  {
    path: "home",
    loadComponent: () => import('@app/pages/custodian/home/home.component').then(m => m.HomeComponent),
    pathMatch: "full",
    data: {pageTitle: "Home"},
  },
  {
    path: "",
    loadComponent: () => import('@app/pages/custodian/home/home.component').then(m => m.HomeComponent),
    pathMatch: "full",
    data: {pageTitle: "Home"},
  },
  {
    path: "settings",
    loadComponent: () => import('@app/pages/custodian/settings/settings.component').then(m => m.CustodianSettingsComponent),
    pathMatch: "full",
    data: {pageTitle: "Settings"},
  },
  {
    path: "requests",
    loadComponent: () => import('@app/pages/custodian/identity-access-requests/identity-access-requests.component').then(m => m.IdentityAccessRequestsComponent),
    pathMatch: "full",
    data: {pageTitle: "Requests"},
    resolve: {
      PreferenceResolver, NodeResolver, RtipsResolver: RTipsResolver, IarsResolver: IarResolver
    },
  }
];