import {Component, OnInit, inject, viewChild} from "@angular/core";
import {DatePipe} from "@angular/common";
import {TranslatePipe, TranslateService} from "@ngx-translate/core";
import {auditlogResolverModel} from "@app/models/resolvers/auditlog-resolver-model";
import {HttpService} from "@app/shared/services/http.service";
import {UtilsService} from "@app/shared/services/utils.service";
import {PaginatedInterfaceComponent} from "@app/shared/components/paginated-interface/paginated-interface.component";
import {TableHeaderComponent} from "@app/shared/components/table/table-header.component";
import {TableFilterOption, TableState} from "@app/shared/components/table/table-state";

/**
 * Who acted is resolved from its identifier and kept on the row, so that the
 * column sorts and filters on what is read.
 */
interface AuditLogRow extends auditlogResolverModel {
  username: string;
}

/**
 * The audit log of the account in session: what the user did, what an
 * administrator or the system did on the account, and what whoever used the
 * account did on its behalf.
 */
@Component({
    selector: "src-preference-tab3",
    templateUrl: "./preference-tab3.component.html",
    standalone: true,
    imports: [DatePipe, PaginatedInterfaceComponent, TableHeaderComponent, TranslatePipe]
})
export class PreferenceTab3Component implements OnInit {
  private readonly httpService = inject(HttpService);
  private readonly translateService = inject(TranslateService);
  protected readonly utilsService = inject(UtilsService);

  auditLog: AuditLogRow[] = [];

  // What the list shows: column filters, search and ordering alike
  private readonly list = viewChild.required<PaginatedInterfaceComponent<AuditLogRow>>(PaginatedInterfaceComponent);

  userOptions: TableFilterOption[] = [];

  readonly severityOptions: TableFilterOption[] = [
    {id: "Low", label: "Low"},
    {id: "Medium", label: "Medium"},
    {id: "High", label: "High"}
  ];

  readonly table = new TableState<AuditLogRow>({
    orderBy: "date",
    orderDesc: true,
    filters: {
      date: {type: "daterange"},
      severity: {type: "select", value: entry => this.utilsService.getAuditLogCategory(entry.type)},
      username: {type: "select"}
    }
  });

  ngOnInit() {
    this.httpService.requestUserAuditLogResource().subscribe(entries => {
      this.auditLog = entries.map(entry => ({...entry, username: this.getUsername(entry)}));

      this.userOptions = Array.from(new Set(this.auditLog.map(entry => entry.username)))
        .sort((a, b) => a.localeCompare(b))
        .map(name => ({id: name, label: name}));

      this.table.setItems(this.auditLog);
    });
  }

  getUsername(entry: auditlogResolverModel): string {
    if (entry.user_id === "system") {
      return this.translateService.instant("system");
    }

    return entry.username || entry.user_id || "";
  }

  getTypeDotColor(type: string): string {
    switch (this.utilsService.getAuditLogCategory(type)) {
      case "Low":
        return "text-info";
      case "Medium":
        return "text-warning";
      case "High":
        return "text-danger";
      default:
        return "text-primary";
    }
  }

  exportAuditLog() {
    this.utilsService.generateCSV("auditlog", this.list().filteredItems, ["date", "type", "username", "user_id", "object_id", "data"]);
  }
}
