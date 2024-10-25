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
  fromLastBackup: boolean = false;

  constructor(private readonly httpService: HttpService, protected authenticationService: AuthenticationService, private auditLogResolver: AuditLogResolver, protected nodeResolver: NodeResolver, protected utilsService: UtilsService) {
  }

  ngOnInit() {
    this.loadAuditLogData();
  }

  loadAuditLogData() {
    console.log("Loading audit log data");
    if (Array.isArray(this.auditLogResolver.dataModel)) {
      this.auditLog = this.auditLogResolver.dataModel;
    } else {
      this.auditLog = [this.auditLogResolver.dataModel];
    }
  }

  fetchAuditLogData(): void {
    console.log(this.fromLastBackup);
    // TODO: remove
    this.fromLastBackup = false;
    // TODO: end remove
    if (this.fromLastBackup) {
      this.httpService.requestAdminAuditLogResourceFromLastBackup().subscribe((data) => {
        this.auditLog = Array.isArray(data) ? data : [data];
      });
      console.log("AuditLog from last backup: ", this.auditLog);
    } else {
      this.loadAuditLogData();
      console.log("AuditLog: ", this.auditLog);
    }
  }

  onCheckboxChange(): void {
    console.log("Checkbox changed: ", this.fromLastBackup);
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
