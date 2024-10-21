import {NgModule} from "@angular/core";
import {RouterModule, Routes} from "@angular/router";
import {HomeComponent} from "@app/pages/analyst/home/home.component";
import {StatisticsComponent} from "@app/pages/analyst/statistics/statistics.component";
import {PreferencesComponent} from "@app/shared/partials/preferences/preferences.component";
import {PreferenceResolver} from "@app/shared/resolvers/preference.resolver";
import {RTipsResolver} from "@app/shared/resolvers/r-tips-resolver.service";
import {StatisticsResolver} from "@app/shared/resolvers/statistics.resolver";
import { ReportsComponent } from "@app/pages/analyst/reports/reports.component";
const routes: Routes = [
  {
    path: "",
    component: HomeComponent,
    pathMatch: "full",
    data: {pageTitle: "Home"},
  },
  {
    path: "home",
    component: HomeComponent,
    pathMatch: "full",
    resolve: {
      PreferenceResolver, RTipsResolver
    },
    data: {pageTitle: "Home"},
  },
  {
    path: "statistics",
    component: StatisticsComponent,
    resolve: {
      StatisticsResolver
    },
    pathMatch: "full",
    data: {pageTitle: "statistics"},
  },
  {
    path: "preferences",
    component: PreferencesComponent,
    pathMatch: "full",
    resolve: {
      PreferenceResolver, RTipsResolver
    },
    data: {pageTitle: "Preferences"},
  },
  {
    path: "reports",
    component: ReportsComponent,
    pathMatch: "full",
    data: {pageTitle: "Reports"},
  }
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class AnalystRoutingModule { }
