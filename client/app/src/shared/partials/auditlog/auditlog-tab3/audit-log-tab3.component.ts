import {Component, OnInit, inject} from "@angular/core";
import {UtilsService} from "@app/shared/services/utils.service";
import {TipsResolver} from "@app/shared/resolvers/tips.resolver";
import {tipsResolverModel} from "@app/models/resolvers/tips-resolver-model";
import {AppDataService} from "@app/app-data.service";
import {DatePipe} from "@angular/common";
import {NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {TranslateModule} from "@ngx-translate/core";
import {PaginatedInterfaceComponent} from "@app/shared/components/paginated-interface/paginated-interface.component";
import {TableHeaderComponent} from "@app/shared/components/table/table-header.component";
import {TableFilterOption, TableState} from "@app/shared/components/table/table-state";

@Component({
    selector: "src-auditlog-tab3",
    templateUrl: "./audit-log-tab3.component.html",
    standalone: true,
    imports: [DatePipe, NgbTooltipModule, PaginatedInterfaceComponent, TableHeaderComponent, TranslateModule]
})
export class AuditLogTab3Component implements OnInit {
  private tipsResolver = inject(TipsResolver);
  protected utilsService = inject(UtilsService);
  protected appDataService = inject(AppDataService);

  tips: tipsResolverModel[] = [];

  channelOptions: TableFilterOption[] = [];

  readonly table = new TableState<tipsResolverModel>({
    orderBy: "creation_date",
    orderDesc: true,
    filters: {
      creation_date: {type: "daterange"},
      last_update: {type: "daterange"},
      expiration_date: {type: "daterange"},
      context_id: {type: "select"}
    }
  });

  ngOnInit() {
    this.loadAuditLogData();
  }

  loadAuditLogData() {
    if (Array.isArray(this.tipsResolver.dataModel)) {
      this.tips = this.tipsResolver.dataModel;
    } else {
      this.tips = [this.tipsResolver.dataModel];
    }

    this.channelOptions = Array.from(new Set(this.tips.map(tip => tip.context_id)),
      id => ({id, label: this.appDataService.contexts_by_id[id]?.name || id}));
    this.table.setItems(this.tips);
  }

  exportAuditLog() {
    this.utilsService.generateCSV('reports', this.tips);
  }
}
