import {Component, OnInit} from "@angular/core";
import {auditlogResolverModel} from "@app/models/resolvers/auditlog-resolver-model";
import {AuditLogResolver} from "@app/shared/resolvers/audit-log-resolver.service";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {UtilsService} from "@app/shared/services/utils.service";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import { HttpService } from "@app/shared/services/http.service";

@Component({
  selector: "src-auditlog-tab1",
  templateUrl: "./audit-log-tab1.component.html"
})
export class AuditLogTab1Component implements OnInit {
  currentPage = 1;
  pageSize = 20;
  auditLog: auditlogResolverModel[] = [];
  isBackupEnabled: boolean = false;
  fromLastBackup: boolean = false;

  constructor(private readonly httpService: HttpService, protected authenticationService: AuthenticationService, private readonly auditLogResolver: AuditLogResolver, protected nodeResolver: NodeResolver, protected utilsService: UtilsService) {
  }

  ngOnInit() {
    this.isBackupEnabled = this.nodeResolver.dataModel.backup_enabled;
    this.loadAuditLogData();
  }

  loadAuditLogData() {
    if (Array.isArray(this.auditLogResolver.dataModel)) {
      this.auditLog = this.auditLogResolver.dataModel;
    } else {
      this.auditLog = [this.auditLogResolver.dataModel];
    }
  }

  fetchAuditLogData(): void {
    if (this.fromLastBackup) {
      this.httpService.requestAdminAuditLogResourceFromLastBackup().subscribe((data) => {
        this.auditLog = Array.isArray(data) ? data : [data];
      });
    } else {
      this.loadAuditLogData();
    }
    this.currentPage = 1;
  }

  onCheckboxChange(): void {
    this.fetchAuditLogData();
  }

  getPaginatedData(): auditlogResolverModel[] {
    const startIndex = (this.currentPage - 1) * this.pageSize;
    const endIndex = startIndex + this.pageSize;
    return this.auditLog.slice(startIndex, endIndex);
  }

  exportAuditLog() {
    this.utilsService.generateCSV(JSON.stringify(this.auditLog), 'auditlog', ["Date", "Type", "User", "Object", "data"]);
  }
}
