import { Component, OnInit } from "@angular/core";
import { nodeResolverModel } from "@app/models/resolvers/node-resolver-model";
import { NodeResolver } from "@app/shared/resolvers/node.resolver";
import { UtilsService } from "@app/shared/services/utils.service";

@Component({
    selector: "src-backup-tab1",
    templateUrl: "./backup-tab1.component.html"
})
export class BackupTab1Component implements OnInit {
    nodeData: nodeResolverModel;
    backupEnable: boolean = false;
    backupTime: string = '';
    backupDestinationPath: string = '';

    constructor(private nodeResolver: NodeResolver, protected utilsService: UtilsService) {}

    ngOnInit(): void {
        this.nodeData = this.nodeResolver.dataModel;
        this.loadBackupInterval();
    }

    loadBackupInterval() {

        this.backupEnable = this.nodeData.backup_enable;
        this.backupTime = this.formatBackupTime(this.nodeData.backup_time_ISO_8601);
        this.backupDestinationPath = this.nodeData.backup_destination_path;
    }

    formatBackupTime(iso8601: string): string {
        const match = iso8601.match(/(?:T)?(\d{2}):(\d{2})/);
        return match ? `${match[1]}:${match[2]}` : '00:00';
    }

    save(): void {
        
        this.nodeData.backup_enable = this.backupEnable;
        this.nodeData.backup_time_ISO_8601 = this.backupTime;
        this.nodeData.backup_destination_path = this.backupDestinationPath;

        try {
            this.utilsService.updateNode(this.nodeData);
        } catch (error) {
            console.error('Error saving backup settings', error);
        }
    }
}