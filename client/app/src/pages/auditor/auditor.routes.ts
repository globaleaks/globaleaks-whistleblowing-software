import {Routes} from "@angular/router";
import {AuditLogResolver} from "@app/shared/resolvers/audit-log-resolver.service";
import {JobResolver} from "@app/shared/resolvers/job.resolver";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {PreferenceResolver} from "@app/shared/resolvers/preference.resolver";
import {RTipsResolver} from "@app/shared/resolvers/r-tips-resolver.service";
import {TipsResolver} from "@app/shared/resolvers/tips.resolver";
import {UsersResolver} from "@app/shared/resolvers/users.resolver";
export const auditorRoutes: Routes = [
  {
    path: "",
    loadComponent: () => import('@app/pages/auditor/home/home.component').then(m => m.HomeComponent),
    pathMatch: "full",
    data: {pageTitle: "Home"},
  },
  {
    path: "home",
    loadComponent: () => import('@app/pages/auditor/home/home.component').then(m => m.HomeComponent),
    pathMatch: "full",
    resolve: {
      PreferenceResolver, RTipsResolver
    },
    data: {pageTitle: "Home"},
  },
  {
    path: "auditlog",
    loadComponent: () => import('@app/pages/admin/auditlog/audit-log.component').then(m => m.AuditLogComponent),
    resolve: {
      NodeResolver, PreferenceResolver, UsersResolver, AuditLogResolver, JobResolver, TipsResolver
    },
    pathMatch: "full",
    data: {sidebar: "auditor-sidebar", pageTitle: "Audit log"},
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