import { AfterViewInit, Component, TemplateRef, ViewChild } from "@angular/core";
import { Tab } from "@app/models/component-model/tab";
import { BackupTab1Component } from "@app/pages/admin/backup/backup-tab1/backup-tab1.component";

@Component({
    selector: "src-backup",
    templateUrl: "./backup.component.html"
})
export class BackupComponent implements AfterViewInit {
    @ViewChild("tab1") tab1!: TemplateRef<BackupTab1Component>;

    tabs: Tab[] = [];
    active: string;


    ngAfterViewInit(): void {
        setTimeout(() => {
            this.active = "Options";
            this.tabs = [
                {
                    id: "options",
                    title: "Options",
                    component: this.tab1
                }
            ];
        });
    }
}