import {Component, OnInit, inject} from "@angular/core";
import {auditlogResolverModel} from "@app/models/resolvers/auditlog-resolver-model";
import {AuditLogResolver} from "@app/shared/resolvers/audit-log-resolver.service";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {UtilsService} from "@app/shared/services/utils.service";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {DatePipe} from "@angular/common";
import {NgbPagination, NgbPaginationPrevious, NgbPaginationNext, NgbPaginationFirst, NgbPaginationLast, NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {TranslateModule} from "@ngx-translate/core";

@Component({
    selector: "src-auditlog-tab1",
    templateUrl: "./audit-log-tab1.component.html",
    standalone: true,
    imports: [NgbPagination, NgbPaginationPrevious, NgbPaginationNext, NgbPaginationFirst, NgbPaginationLast, NgbTooltipModule, DatePipe, TranslatorPipe, TranslateModule]
})
export class AuditLogTab1Component implements OnInit {
  protected authenticationService = inject(AuthenticationService);
  private auditLogResolver = inject(AuditLogResolver);
  protected nodeResolver = inject(NodeResolver);
  protected utilsService = inject(UtilsService);

  currentPage = 1;
  pageSize = 20;
  auditLog: auditlogResolverModel[] = [];

  ngOnInit() {
    this.loadAuditLogData();
  }

  loadAuditLogData() {
    if (Array.isArray(this.auditLogResolver.dataModel)) {
      this.auditLog = this.auditLogResolver.dataModel;
    } else {
      this.auditLog = [this.auditLogResolver.dataModel];
    }
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
