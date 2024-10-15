import {NgModule} from "@angular/core";
import {RouterModule, Routes} from "@angular/router";
import {adminHomeComponent} from "@app/pages/admin/home/admin-home.component";
import {SettingsModule} from "@app/pages/admin/settings/settings.module";
import {UsersModule} from "@app/pages/admin/users/users.module";
import {ContextsModule} from "@app/pages/admin/contexts/contexts.module";
import {CaseManagementModule} from "@app/pages/admin/casemanagement/case-management.module";
import {AuditLogModule} from "@app/pages/admin/auditlog/audit-log.module";
import {NotificationsModule} from "@app/pages/admin/notifications/notifications.module";
import {SitesModule} from "@app/pages/admin/sites/sites.module";
import {NetworkModule} from "@app/pages/admin/network/network.module";
import {QuestionnairesModule} from "@app/pages/admin/questionnaires/questionnaires.module";
import {AdminPreferencesComponent} from "@app/pages/admin/admin-preferences/admin-preferences.component";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {PreferenceResolver} from "@app/shared/resolvers/preference.resolver";
import {UsersResolver} from "@app/shared/resolvers/users.resolver";
import {QuestionnairesResolver} from "@app/shared/resolvers/questionnaires.resolver";
import {ContextsResolver} from "@app/shared/resolvers/contexts.resolver";
import {AuditLogResolver} from "@app/shared/resolvers/audit-log-resolver.service";
import {JobResolver} from "@app/shared/resolvers/job.resolver";
import {TipsResolver} from "@app/shared/resolvers/tips.resolver";
import {NotificationsResolver} from "@app/shared/resolvers/notifications.resolver";
import {NetworkResolver} from "@app/shared/resolvers/network.resolver";
import {RedirectsResolver} from "@app/shared/resolvers/redirects.resolver";
import {FieldTemplatesResolver} from "@app/shared/resolvers/field-templates-resolver.service";
import {StatusResolver} from "@app/shared/resolvers/statuses.resolver";
import { BackupModule } from "@app/pages/admin/backup/backup.module";

const routes: Routes = [
  {
    path: "",
    component: adminHomeComponent,
    resolve: {
      NodeResolver, PreferenceResolver, UsersResolver
    },
    pathMatch: "full",
    data: {sidebar: "admin-sidebar", pageTitle: "Home"},
  },
  {
    path: "home",
    component: adminHomeComponent,
    resolve: {
      NodeResolver, PreferenceResolver, UsersResolver
    },
    pathMatch: "full",
    data: {sidebar: "admin-sidebar", pageTitle: "Home"},
  },
  {
    path: "preferences",
    component: AdminPreferencesComponent,
    resolve: {
      NodeResolver, PreferenceResolver
    },
    pathMatch: "full",
    data: {pageTitle: "Preferences"},
  },
  {
    path: "settings",
    loadChildren: () => SettingsModule,
    resolve: {
      NodeResolver, PreferenceResolver, UsersResolver, QuestionnairesResolver
    },
    pathMatch: "full",
    data: {sidebar: "admin-sidebar", pageTitle: "Settings"},
  },
  {
    path: "sites",
    loadChildren: () => SitesModule,
    resolve: {
      NodeResolver, PreferenceResolver, UsersResolver, JobResolver, TipsResolver, QuestionnairesResolver, StatusResolver
    },
    pathMatch: "full",
    data: {sidebar: "admin-sidebar", pageTitle: "Sites"},
  },
  {
    path: "users",
    loadChildren: () => UsersModule,
    resolve: {
      NodeResolver, PreferenceResolver, UsersResolver
    },
    pathMatch: "full",
    data: {sidebar: "admin-sidebar", pageTitle: "Users"},
  },
  {
    path: "questionnaires",
    loadChildren: () => QuestionnairesModule,
    resolve: {
      NodeResolver, PreferenceResolver, ContextsResolver, UsersResolver, QuestionnairesResolver, FieldTemplatesResolver
    },
    pathMatch: "full",
    data: {sidebar: "admin-sidebar", pageTitle: "Questionnaires"},
  },
  {
    path: "channels",
    loadChildren: () => ContextsModule,
    resolve: {
      NodeResolver, PreferenceResolver, UsersResolver, QuestionnairesResolver, ContextsResolver
    },
    pathMatch: "full",
    data: {sidebar: "admin-sidebar", pageTitle: "Channels"},
  },
  {
    path: "casemanagement",
    loadChildren: () => CaseManagementModule,
    resolve: {
      NodeResolver, PreferenceResolver, StatuseResolver: StatusResolver
    },
    pathMatch: "full",
    data: {sidebar: "admin-sidebar", pageTitle: "Case management"},
  },
  {
    path: "auditlog",
    loadChildren: () => AuditLogModule,
    resolve: {
      NodeResolver, PreferenceResolver, UsersResolver, AuditlogResolver: AuditLogResolver, JobResolver, TipsResolver
    },
    pathMatch: "full",
    data: {sidebar: "admin-sidebar", pageTitle: "Audit log"},
  },
  {
    path: "notifications",
    loadChildren: () => NotificationsModule,
    resolve: {
      NodeResolver, PreferenceResolver, NotificationsResolver
    },
    pathMatch: "full",
    data: {sidebar: "admin-sidebar", pageTitle: "Notifications"},
  },
  {
    path: "network",
    loadChildren: () => NetworkModule,
    resolve: {
      NodeResolver, PreferenceResolver, UsersResolver, NetworkResolver, RedirectsResolver
    },
    pathMatch: "full",
    data: {sidebar: "admin-sidebar", pageTitle: "Network"},
  },
  {
    path: "backup",
    loadChildren: () => BackupModule,
    resolve: {
      NodeResolver, PreferenceResolver
    },
    pathMatch: "full",
    data: {sidebar: "admin-sidebar", pageTitle: "Backup"},
  }
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule],
})
export class AdminRoutingModule {
}
