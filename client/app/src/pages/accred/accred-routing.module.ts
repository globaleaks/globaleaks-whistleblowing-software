import {NgModule} from "@angular/core";
import {RouterModule, Routes} from "@angular/router";
import {AccredComponent} from "@app/pages/accred/accred/accred.component";

const routes: Routes = [
  {
    path: "",
    component: AccredComponent,
    pathMatch: "full",
  }

];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule],
})
export class AccredRoutingModule {
}
