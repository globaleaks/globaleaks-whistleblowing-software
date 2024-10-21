import {Routes} from "@angular/router";

export const wizardRoutes: Routes = [
  {
    path: "",
    loadComponent: () => import('@app/pages/wizard/wizard/wizard.component').then(m => m.WizardComponent),
    pathMatch: "full",
  }
];