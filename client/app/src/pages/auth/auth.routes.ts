import {Routes} from "@angular/router";

export const authRoutes: Routes = [
  {
    path: "",
    loadComponent: () => import('@app/pages/auth/login/login.component').then(m => m.LoginComponent),
    pathMatch: "full",
    data: {pageTitle: "Log in"},
  },
  {
    path: "passwordreset",
    loadComponent: () => import('@app/pages/auth/password-reset/password-reset.component').then(m => m.PasswordResetComponent),
    pathMatch: "full",
    data: {pageTitle: "Password reset"},
  },
  {
    path: "passwordreset/requested",
    loadComponent: () => import('@app/pages/auth/password-reset-requested/password-reset-requested.component').then(m => m.PasswordRequestedComponent),
    pathMatch: "full",
    data: {pageTitle: "Password reset"},
  }
];
