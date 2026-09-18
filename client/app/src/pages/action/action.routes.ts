import {Routes} from "@angular/router";
import {PreferenceResolver} from "@app/shared/resolvers/preference.resolver";

export const actionRoutes: Routes = [
  {
    path: "forcedtwofactor",
    loadComponent: () => import('@app/pages/action/forced-two-factor/forced-two-factor.component').then(m => m.ForcedTwoFactorComponent),
    pathMatch: "full",
    resolve: {
      PreferenceResolver
    },
    data: {pageTitle: "Password reset"},
  }, {
    path: "forcedpasswordchange",
    loadComponent: () => import('@app/pages/action/force-password-change/force-password-change.component').then(m => m.ForcePasswordChangeComponent),
    pathMatch: "full",
    resolve: {
      PreferenceResolver
    },
    data: {pageTitle: "Password reset"},
  }
];