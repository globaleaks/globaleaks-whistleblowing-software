import {Component, OnInit, inject} from "@angular/core";
import {ActivatedRoute} from "@angular/router";
import {auditlogResolverModel} from "@app/models/resolvers/auditlog-resolver-model";
import {AuditLogResolver} from "@app/shared/resolvers/audit-log-resolver.service";
import {UsersResolver} from "@app/shared/resolvers/users.resolver";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {User} from "@app/models/resolvers/user-resolver-model";
import {UtilsService} from "@app/shared/services/utils.service";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {DatePipe} from "@angular/common";
import {TranslateModule, TranslateService} from "@ngx-translate/core";
import {PaginatedInterfaceComponent} from "@app/shared/components/paginated-interface/paginated-interface.component";
import {TableHeaderComponent} from "@app/shared/components/table/table-header.component";
import {TableFilterOption, TableState} from "@app/shared/components/table/table-state";

/**
 * The username of who acted is resolved from its identifier: it is kept on
 * the row so that the column sorts and filters on what is read, not on the id.
 */
interface AuditLogRow extends auditlogResolverModel {
  username: string;
}


@Component({
    selector: "src-auditlog-tab1",
    templateUrl: "./audit-log-tab1.component.html",
    standalone: true,
    imports: [DatePipe, PaginatedInterfaceComponent, TableHeaderComponent, TranslateModule]
})
export class AuditLogTab1Component implements OnInit {
  protected authenticationService = inject(AuthenticationService);
  private auditLogResolver = inject(AuditLogResolver);
  private usersResolver = inject(UsersResolver);
  protected nodeResolver = inject(NodeResolver);
  protected utilsService = inject(UtilsService);
  private translateService = inject(TranslateService);
  private activatedRoute = inject(ActivatedRoute);

  auditLog: AuditLogRow[] = [];

  userOptions: TableFilterOption[] = [];

  users: User[] = [];

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
    this.loadUsersData();
    this.loadAuditLogData();
    // A link may point at the entries of one user: the column filter is the
    // one place holding that selection
    this.activatedRoute.queryParams.subscribe(params => {
      const user = this.users.find(u => u.id === params["user"]);
      if (user) {
        this.table.setSelection("username", [{id: user.username, label: user.username}]);
      }
    });
  }

  loadUsersData() {
    this.users = this.usersResolver.dataModel;
  }

  loadAuditLogData() {
    const entries = Array.isArray(this.auditLogResolver.dataModel) ?
      this.auditLogResolver.dataModel :
      [this.auditLogResolver.dataModel];

    this.auditLog = entries.map(entry => ({...entry, username: this.getUsername(entry.type, entry.user_id || "")}));

    this.userOptions = Array.from(new Set(this.auditLog.map(entry => entry.username)))
      .sort((a, b) => a.localeCompare(b))
      .map(name => ({id: name, label: name}));

    this.table.setItems(this.auditLog);
  }

  /**
   * The audit log of the platform names who acted by its username: it is
   * unique within the tenant and does not change, while the name is neither
   * of the two and would make the attribution of an entry ambiguous.
   */
  getUsername(logType:string, userId: string): string {
    if (userId === 'system') {
      return this.translateService.instant('system');
    } else if (logType.startsWith('whistleblower')) {
      return this.translateService.instant('Whistleblower');
    }

    const user = this.users.find(u => u.id === userId);
    if (user) {
      return user.username;
    }

    // Return the ID if user not found (might be deleted user)
    return userId;
  }

  getTypeDotColor(type: string): string {
    const category = this.utilsService.getAuditLogCategory(type);

    switch(category) {
      case 'Low':
        return 'text-info';
      case 'Medium':
        return 'text-warning';
      case 'High':
        return 'text-danger';
      default:
        return 'text-primary';
    }
  }

  exportAuditLog() {
    // The username is exported along with the identifier: the first is the one
    // the entry is read by, the second the one it stays tied to
    this.utilsService.generateCSV('auditlog', this.auditLog, ['date', 'type', 'username', 'user_id', 'object_id', 'data']);
  }
}
