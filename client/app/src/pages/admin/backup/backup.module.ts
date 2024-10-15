import { CommonModule } from "@angular/common";
import { NgModule } from "@angular/core";
import { FormsModule } from "@angular/forms";
import { BackupTab1Component } from "@app/pages/admin/backup/backup-tab1/backup-tab1.component";
import { BackupComponent } from "@app/pages/admin/backup/backup.component";
import { NgbNavModule } from "@ng-bootstrap/ng-bootstrap";
import { TranslateModule } from "@ngx-translate/core";
import { BackupRoutingModule } from "./backup-routing.module";

@NgModule({
    declarations: [
        BackupComponent,
        BackupTab1Component
    ],
    imports: [
        CommonModule,
        FormsModule,
        NgbNavModule,
        TranslateModule,
        BackupRoutingModule
    ]
})
export class BackupModule {
}