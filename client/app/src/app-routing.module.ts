import {NgModule} from "@angular/core";
import {RouterModule, Routes} from "@angular/router";
import {SessionGuard} from "@app/app-guard.service";
import {HomeComponent} from "@app/pages/dashboard/home/home.component";
import {
  PasswordResetResponseComponent
} from "@app/pages/auth/password-reset-response/password-reset-response.component";
import {AdminGuard} from "@app/shared/guards/admin.guard";
import {CustodianGuard} from "@app/shared/guards/custodian.guard";
import {ReceiverGuard} from "@app/shared/guards/receiver.guard";
import {AnalystGuard} from "@app/shared/guards/analyst.guard";
import {PreferenceResolver} from "@app/shared/resolvers/preference.resolver";
import {Pageguard} from "@app/shared/guards/pageguard.service";
import {ActivationComponent} from "@app/pages/signup/templates/activation/activation.component";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {RTipsResolver} from "@app/shared/resolvers/r-tips-resolver.service";
import {TipComponent} from "@app/pages/recipient/tip/tip.component";
import { TipEoComponent } from "@app/pages/recipient/tip-eo/tip-eo.component";
import {TitleResolver} from "@app/shared/resolvers/title-resolver.resolver";
import {IarResolver} from "@app/shared/resolvers/iar-resolver.service";
import {BlankComponent} from "@app/shared/blank/blank.component";
import {WbTipResolver} from "@app/shared/resolvers/wb-tip-resolver.service";
import {WhistleblowerLoginResolver} from "@app/shared/resolvers/whistleblower-login.resolver";
import {SubmissionComponent} from "@app/pages/whistleblower/submission/submission.component";
import {AuthRoutingModule} from "@app/pages/auth/auth-routing.module";
import { AccreditorGuard } from "./shared/guards/accreditor.guard";
import { OrganizationComponent } from "@app/pages/accreditor/organization/organization.component";
import { SendtipComponent } from "./pages/recipient/sendtip/sendtip.component";
import { SendtipDetailComponent } from "./pages/recipient/sendtip-detail/sendtip-detail.component";
import { AccredRoutingGuard } from "./pages/accred/accred.guard";

const routes: Routes = [
  {
    path: "blank",
    pathMatch: "full",
    component: BlankComponent
  },
  {
    path: "",
    canActivate: [Pageguard],
    component: HomeComponent,
    data: {pageTitle: ""},
    pathMatch: "full",
    resolve: {
      WbTipResolver, WhistleblowerLoginResolver
    }
  },
  {
    path: "submission",
    canActivate: [Pageguard],
    component: SubmissionComponent,
    data: {pageTitle: ""},
    pathMatch: "full",
    resolve: {
      WbTipResolver, WhistleblowerLoginResolver
    }
  },
  {
    path: "login",
    canActivate: [Pageguard],
    data: {pageTitle: "Log in"},
    loadChildren: () => AuthRoutingModule,
  },
  {
    path: "signup",
    data: {pageTitle: "Sign up"},
    resolve: {
      PreferenceResolver
    },
    loadChildren: () => import("./pages/signup/signup-routing.module").then(m => m.SignupRoutingModule)

  },
  {
    path: "action",
    loadChildren: () => import("./pages/action/action-routing.module").then(m => m.ActionRoutingModule)
  },
  {
    path: "recipient",
    canActivate: [ReceiverGuard],
    loadChildren: () => import("./pages/recipient/recipient-routing.module").then(m => m.RecipientRoutingModule),
    data: {
      sidebar: "recipient-sidebar"
    }
  },
  {
    path: "custodian",
    canActivate: [CustodianGuard],
    resolve: {
      PreferenceResolver, NodeResolver, RtipsResolver: RTipsResolver, IarsResolver: IarResolver
    },
    loadChildren: () => import("./pages/custodian/custodian-routing.module").then(m => m.CustodianRoutingModule),
    data: {
      sidebar: "custodian-sidebar",
      pageTitle: "Home",
    },
  },
  {
    path: "analyst",
    canActivate: [AnalystGuard],
    loadChildren: () => import("./pages/analyst/analyst-routing.module").then(m => m.AnalystRoutingModule),
    data: {
      sidebar: "analyst-sidebar",
      pageTitle: "Home",
    },
  },
  {
    path: "admin",
    canActivate: [AdminGuard],
    loadChildren: () => import("./pages/admin/admin-routing.module").then(m => m.AdminRoutingModule),
    data: {
      sidebar: "admin-sidebar",
      pageTitle: "Log in",
    },
  },
  {
    path: "password/reset",
    data: {pageTitle: "Password reset"},
    component: PasswordResetResponseComponent,
  },
  {
    path: "activation",
    data: {pageTitle: "Sign up"},
    component: ActivationComponent,
  },
  {
    path: "wizard",
    data: {pageTitle: "Platform wizard"},
    resolve: {
      PreferenceResolver,
      title: TitleResolver
    },
    loadChildren: () => import("./pages/wizard/wizard-routing.module").then(m => m.WizardRoutingModule)
  },
  {
    path: "accreditation-request",
    data: {pageTitle: "Accreditation"},
    canActivate: [AccredRoutingGuard],
    resolve: {
      PreferenceResolver,
      title: TitleResolver
    },
    loadChildren: () => import("./pages/accred/accred-routing.module").then(m => m.AccredRoutingModule)
  },
  {
    path: "accreditation-request/:org_id",
    data: {pageTitle: "Accreditation"},
    canActivate: [AccredRoutingGuard],
    resolve: {
      PreferenceResolver,
      title: TitleResolver
    },
    loadChildren: () => import("./pages/accred/accred-routing.module").then(m => m.AccredRoutingModule)
  },
  {
    path: "reports/:tip_id",
    data: {pageTitle: "Report"},
    resolve: {
      PreferenceResolver,
    },
    component: TipComponent,
    canActivate: [SessionGuard],
    pathMatch: "full",
  },
  { 
    path: 'accreditor', 
    canActivate: [AccreditorGuard],
    data: {
      sidebar: "accreditor-sidebar",
      pageTitle: "Home",
    },
    loadChildren: () => import('./pages/accreditor/accreditor-routing.module').then(m => m.AccreditorRoutingModule) 
  },
  {
    path: "organizations/:org_id",
    data: {pageTitle: "Organization"},
    component: OrganizationComponent,
    canActivate: [AccreditorGuard],
    pathMatch: "full",
  },
  {
    path: "reports-eo/:tip_id",
    data: {pageTitle: "Report"},
    resolve: {
      PreferenceResolver,
    },
    component: TipEoComponent,
    canActivate: [SessionGuard],
    pathMatch: "full",
  },
  {
    path: "sendtip",
    data: {pageTitle: "Send tip"},
    component: SendtipComponent,
    canActivate: [SessionGuard],
    pathMatch: "full",
  },
  {
    path: "sendtip-detail",
    data: {pageTitle: "Sent tip detail"},
    component: SendtipDetailComponent,
    canActivate: [SessionGuard],
    pathMatch: "full",
  },
  {path: "**", redirectTo: ""}
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule],
})
export class AppRoutingModule {

}
