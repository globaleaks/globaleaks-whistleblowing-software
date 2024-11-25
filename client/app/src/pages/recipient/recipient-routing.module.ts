import {NgModule} from "@angular/core";
import {RouterModule, Routes} from "@angular/router";
import {HomeComponent} from "@app/pages/recipient/home/home.component";
import {TipsComponent} from "@app/pages/recipient/tips/tips.component";
import {SettingsComponent} from "@app/pages/recipient/settings/settings.component";
import {PreferencesComponent} from "@app/shared/partials/preferences/preferences.component";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {PreferenceResolver} from "@app/shared/resolvers/preference.resolver";
import {RTipsResolver} from "@app/shared/resolvers/r-tips-resolver.service";
import { AccreditationRequestComponent } from "@app/pages/recipient/accreditation-request/accreditation-request.component";
import { RecipientRoutingGuard } from "./recipient.guard";
import { TipEoComponent } from "./tip-eo/tip-eo.component";
import { TipComponent } from "./tip/tip.component";

const routes: Routes = [
  {
    path: "",
    component: HomeComponent,
    pathMatch: "full",
    data: {pageTitle: "Home"},
    resolve: {
      PreferenceResolver, RTipsResolver
    },
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
    path: "reports",
    component: TipsComponent,
    pathMatch: "full",
    resolve: {
      PreferenceResolver, RTipsResolver
    },
    data: {pageTitle: "Reports"},
  },
  {
    path: "accreditation",
    component: AccreditationRequestComponent,
    pathMatch: "full",
    resolve: {
      PreferenceResolver
    },
    data: {pageTitle: "Accreditation Request"},
  },
  {
    path: "settings",
    component: SettingsComponent,
    resolve: {
      NodeResolver
    },
    pathMatch: "full",
    data: {pageTitle: "Settings"},
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
    path: 'reports/:tip_id',
    component: TipComponent,
    canActivate: [RecipientRoutingGuard],
    resolve: {
      PreferenceResolver
    },
  },
  {
    path: 'tip/:tip_id',
    component: TipComponent,
  },
  {
    path: 'tip-eo/:tip_id',
    component: TipEoComponent,
  }
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule],
  providers: [RecipientRoutingGuard]
})
export class RecipientRoutingModule {
}
