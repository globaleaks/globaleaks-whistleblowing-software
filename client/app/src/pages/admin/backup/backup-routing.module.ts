import { NgModule } from "@angular/core";
import { BackupComponent } from "@app/pages/admin/backup/backup.component";
import { RouterModule, Routes } from "@angular/router";

const routes: Routes = [
    {
        path: "",
        component: BackupComponent,
        pathMatch: "full",
    }
];

@NgModule({
    imports: [RouterModule.forChild(routes)],
    exports: [RouterModule]
})
export class BackupRoutingModule {
}