import {Component, OnInit, inject} from "@angular/core";
import {UtilsService} from "@app/shared/services/utils.service";
import {TipsResolver} from "@app/shared/resolvers/tips.resolver";
import {UsersResolver} from "@app/shared/resolvers/users.resolver";
import {tipsResolverModel} from "@app/models/resolvers/tips-resolver-model";
import {AppDataService} from "@app/app-data.service";
import {DatePipe} from "@angular/common";
import {NgbPagination, NgbPaginationPrevious, NgbPaginationNext, NgbPaginationFirst, NgbPaginationLast, NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {TipAuditLogService} from "@app/shared/services/tip-audit-log.service";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {TranslateModule} from "@ngx-translate/core";

@Component({
    selector: "src-auditlog-tab3",
    templateUrl: "./audit-log-tab3.component.html",
    standalone: true,
    imports: [NgbPagination, NgbPaginationPrevious, NgbPaginationNext, NgbPaginationFirst, NgbPaginationLast, NgbTooltipModule, DatePipe, TranslatorPipe, TranslateModule]
})
export class AuditLogTab3Component implements OnInit {
  private tipsResolver = inject(TipsResolver);
  private usersResolver = inject(UsersResolver);
  protected utilsService = inject(UtilsService);
  protected appDataService = inject(AppDataService);
  private tipAuditLogService = inject(TipAuditLogService);

  currentPage = 1;
  pageSize = 20;
  tips: tipsResolverModel[] = [];

  ngOnInit() {
    this.loadAuditLogData();
  }

  loadAuditLogData() {
    if (Array.isArray(this.tipsResolver.dataModel)) {
      this.tips = this.tipsResolver.dataModel;
    } else {
      this.tips = [this.tipsResolver.dataModel];
    }
  }

  getPaginatedData(): tipsResolverModel[] {
    const startIndex = (this.currentPage - 1) * this.pageSize;
    const endIndex = startIndex + this.pageSize;
    return this.tips.slice(startIndex, endIndex);
  }

  exportAuditLog() {
    this.utilsService.generateCSV('reports', this.tips);
  }

  openTipAuditLogModal(tip: tipsResolverModel) {
    this.tipAuditLogService.openAuditLogModal({
      tipId: tip.id,
      tipData: tip,
      usersData: this.usersResolver.dataModel || []
    });
  }
}
