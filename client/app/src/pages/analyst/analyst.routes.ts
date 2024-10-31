import {Routes} from "@angular/router";
import {PreferenceResolver} from "@app/shared/resolvers/preference.resolver";
import {RTipsResolver} from "@app/shared/resolvers/r-tips-resolver.service";
import {StatisticsResolver} from "@app/shared/resolvers/statistics.resolver";
export const analystRoutes: Routes = [
  {
    path: "",
    loadComponent: () => import('@app/pages/analyst/home/home.component').then(m => m.HomeComponent),
    pathMatch: "full",
    data: {pageTitle: "Home"},
  },
  {
    path: "home",
    loadComponent: () => import('@app/pages/analyst/home/home.component').then(m => m.HomeComponent),
    pathMatch: "full",
    resolve: {
      PreferenceResolver, RTipsResolver
    },
    data: {pageTitle: "Home"},
  },
  {
    path: "statistics",
    loadComponent: () => import('@app/pages/analyst/statistics/statistics.component').then(m => m.StatisticsComponent),
    resolve: {
      StatisticsResolver
    },
    pathMatch: "full",
    data: {pageTitle: "statistics"},
  },
  {
    path: "preferences",
    loadComponent: () => import('@app/shared/partials/preferences/preferences.component').then(m => m.PreferencesComponent),
    pathMatch: "full",
    resolve: {
      PreferenceResolver, RTipsResolver
    },
    data: {pageTitle: "Preferences"},
  }
];