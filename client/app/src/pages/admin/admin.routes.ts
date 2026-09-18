import {Routes} from "@angular/router";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {PreferenceResolver} from "@app/shared/resolvers/preference.resolver";
import {UsersResolver} from "@app/shared/resolvers/users.resolver";
import {QuestionnairesResolver} from "@app/shared/resolvers/questionnaires.resolver";
import {ContextsResolver} from "@app/shared/resolvers/contexts.resolver";
import {NotificationsResolver} from "@app/shared/resolvers/notifications.resolver";
import {StatisticalTemplatesResolver} from "@app/shared/resolvers/statistical-templates.resolver";
import {StatisticalMetricsResolver} from "@app/shared/resolvers/statistical-metrics.resolver";
import {NetworkResolver} from "@app/shared/resolvers/network.resolver";
import {RedirectsResolver} from "@app/shared/resolvers/redirects.resolver";
import {FieldTemplatesResolver} from "@app/shared/resolvers/field-templates-resolver.service";
import {StatusResolver} from "@app/shared/resolvers/statuses.resolver";
import {SelectablesResolver} from "@app/shared/resolvers/selectables.resolver";
import {AuditLogResolver} from "@app/shared/resolvers/audit-log-resolver.service";
import {AuditLogUsersResolver} from "@app/shared/resolvers/audit-log-users.resolver";
import {JobResolver} from "@app/shared/resolvers/job.resolver";
import {TipsResolver} from "@app/shared/resolvers/tips.resolver";

export const adminRoutes: Routes = [
  {
    path: "",
    loadComponent: () => import('@app/pages/admin/home/admin-home.component').then(m => m.adminHomeComponent),
    resolve: {
      NodeResolver, PreferenceResolver
    },
    pathMatch: "full",
    data: {sidebar: "admin-sidebar", pageTitle: "Home"},
  },
  {
    path: "home",
    loadComponent: () => import('@app/pages/admin/home/admin-home.component').then(m => m.adminHomeComponent),
    resolve: {
      NodeResolver, PreferenceResolver
    },
    pathMatch: "full",
    data: {sidebar: "admin-sidebar", pageTitle: "Home"},
  },
  {
    path: "preferences",
    loadComponent: () => import('@app/pages/admin/admin-preferences/admin-preferences.component').then(m => m.AdminPreferencesComponent),
    resolve: {
      NodeResolver, PreferenceResolver
    },
    pathMatch: "full",
    data: {pageTitle: "Preferences"},
  },
  {
    path: "settings",
    loadComponent: () => import('@app/pages/admin/settings/settings.component').then(m => m.AdminSettingsComponent),
    resolve: {
      NodeResolver, PreferenceResolver, SelectablesResolver
    },
    pathMatch: "full",
    data: {sidebar: "admin-sidebar", pageTitle: "Settings"},
  },
  {
    path: "support",
    loadComponent: () => import('@app/pages/admin/support/support.component').then(m => m.AdminSupportComponent),
    resolve: {
      NodeResolver, PreferenceResolver
    },
    pathMatch: "full",
    data: {sidebar: "admin-sidebar", pageTitle: "Support"},
  },
  {
    path: "sites",
    loadComponent: () => import('@app/pages/admin/sites/sites.component').then(m => m.SitesComponent),
    resolve: {
      NodeResolver, PreferenceResolver
    },
    pathMatch: "full",
    data: {sidebar: "admin-sidebar", pageTitle: "Sites"},
  },
  {
    path: "users",
    loadComponent: () => import('@app/pages/admin/users/users.component').then(m => m.UsersComponent),
    resolve: {
      NodeResolver, PreferenceResolver, UsersResolver
    },
    pathMatch: "full",
    data: {sidebar: "admin-sidebar", pageTitle: "Users"},
  },
  {
    path: "questionnaires",
    loadComponent: () => import('@app/pages/admin/questionnaires/questionnaires.component').then(m => m.QuestionnairesComponent),
    resolve: {
      NodeResolver, PreferenceResolver, QuestionnairesResolver, FieldTemplatesResolver, SelectablesResolver
    },
    pathMatch: "full",
    data: {sidebar: "admin-sidebar", pageTitle: "Questionnaires"},
  },
  {
    path: "channels",
    loadComponent: () => import('@app/pages/admin/contexts/contexts.component').then(m => m.ContextsComponent),
    resolve: {
      NodeResolver, PreferenceResolver, ContextsResolver, SelectablesResolver
    },
    pathMatch: "full",
    data: {sidebar: "admin-sidebar", pageTitle: "Channels"},
  },
  {
    path: "casemanagement",
    loadComponent: () => import('@app/pages/admin/casemanagement/case-management.component').then(m => m.CaseManagementComponent),
    resolve: {
      NodeResolver, PreferenceResolver, StatuseResolver: StatusResolver
    },
    pathMatch: "full",
    data: {sidebar: "admin-sidebar", pageTitle: "Case management"},
  },
  {
    path: "statistics",
    loadComponent: () => import('@app/pages/analyst/statistics/statistics.component').then(m => m.StatisticsComponent),
    resolve: {
      NodeResolver, PreferenceResolver, StatisticalTemplatesResolver, StatisticalMetricsResolver
    },
    pathMatch: "full",
    data: {sidebar: "admin-sidebar", pageTitle: "Statistics"},
  },
  {
    path: "auditlog",
    loadComponent: () => import('@app/shared/partials/auditlog/audit-log.component').then(m => m.AuditLogComponent),
    resolve: {
      NodeResolver, PreferenceResolver, AuditLogUsersResolver, AuditlogResolver: AuditLogResolver, JobResolver, TipsResolver
    },
    pathMatch: "full",
    data: {sidebar: "admin-sidebar", pageTitle: "Audit log"},
  },
  {
    path: "notifications",
    loadComponent: () => import('@app/pages/admin/notifications/notifications.component').then(m => m.NotificationsComponent),
    resolve: {
      NodeResolver, PreferenceResolver, NotificationsResolver
    },
    pathMatch: "full",
    data: {sidebar: "admin-sidebar", pageTitle: "Notifications"},
  },
  {
    path: "network",
    loadComponent: () => import('@app/pages/admin/network/network.component').then(m => m.NetworkComponent),
    resolve: {
      NodeResolver, PreferenceResolver, NetworkResolver, RedirectsResolver
    },
    pathMatch: "full",
    data: {sidebar: "admin-sidebar", pageTitle: "Network"},
  }
];
