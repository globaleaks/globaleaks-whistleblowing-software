import {Component, ChangeDetectionStrategy, ChangeDetectorRef, computed, effect, inject} from "@angular/core";
import {DatePipe} from "@angular/common";
import {AuditLogUsersResolver} from "@app/shared/resolvers/audit-log-users.resolver";
import {User} from "@app/models/resolvers/user-resolver-model";
import {UtilsService} from "@app/shared/services/utils.service";
import {NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {TranslateModule} from "@ngx-translate/core";
import {PaginatedInterfaceComponent} from "@app/shared/components/paginated-interface/paginated-interface.component";
import {TableHeaderComponent} from "@app/shared/components/table/table-header.component";
import {TableFilterOption, TableState} from "@app/shared/components/table/table-state";

@Component({
    changeDetection: ChangeDetectionStrategy.OnPush,
    selector: "src-auditlog-tab2",
    templateUrl: "./audit-log-tab2.component.html",
    standalone: true,
    imports: [DatePipe, NgbTooltipModule, PaginatedInterfaceComponent, TableHeaderComponent, TranslateModule]
})
export class AuditLogTab2Component {
  private utilsService = inject(UtilsService);
  private cdr = inject(ChangeDetectorRef);
  protected usersResolver = inject(AuditLogUsersResolver);

  readonly users = computed(() => this.usersResolver.resource.value());

  roleOptions: TableFilterOption[] = [];

  readonly table = new TableState<User>({
    orderBy: "creation_date",
    orderDesc: true,
    filters: {
      role: {type: "select"},
      creation_date: {type: "daterange"},
      last_login: {type: "daterange"}
    }
  });

  constructor() {
    // The table holds its own filtered result: it is refilled whenever the
    // resource lands, and the view is marked since the state is not a signal
    effect(() => {
      const users = this.users();
      this.roleOptions = Array.from(new Set(users.map(user => user.role)), role => ({id: role, label: role}));
      this.table.setItems(users);
      this.cdr.markForCheck();
    });
  }

  exportAuditLog() {
    this.utilsService.generateCSV('users', this.users());
  }
}
