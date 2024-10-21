import {Routes} from "@angular/router";

export const signupRoutes: Routes = [
  {
    path: "",
    loadComponent: () => import('@app/pages/signup/signup/signup.component').then(m => m.SignupComponent),
    pathMatch: "full",
  },
];