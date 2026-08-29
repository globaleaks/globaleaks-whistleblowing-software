import {Routes} from "@angular/router";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {PreferenceResolver} from "@app/shared/resolvers/preference.resolver";
import {AuditLogUsersResolver} from "@app/shared/resolvers/audit-log-users.resolver";
import {AuditLogResolver} from "@app/shared/resolvers/audit-log-resolver.service";
import {JobResolver} from "@app/shared/resolvers/job.resolver";
import {TipsResolver} from "@app/shared/resolvers/tips.resolver";

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
      PreferenceResolver
    },
    data: {pageTitle: "Home"},
  },
  {
    path: "auditlog",
    loadComponent: () => import('@app/shared/partials/auditlog/audit-log.component').then(m => m.AuditLogComponent),
    resolve: {
      NodeResolver, PreferenceResolver, AuditLogUsersResolver, AuditlogResolver: AuditLogResolver, JobResolver, TipsResolver
    },
    pathMatch: "full",
    data: {sidebar: "auditor-sidebar", pageTitle: "Audit log"},
  },
  {
    path: "preferences",
    loadComponent: () => import('@app/shared/partials/preferences/preferences.component').then(m => m.PreferencesComponent),
    pathMatch: "full",
    resolve: {
      PreferenceResolver
    },
    data: {pageTitle: "Preferences"},
  }
];
