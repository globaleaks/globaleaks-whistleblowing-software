import {Component, computed, inject, ChangeDetectionStrategy} from "@angular/core";
import {DatePipe} from "@angular/common";
import {UsersResolver} from "@app/shared/resolvers/users.resolver";
import {UtilsService} from "@app/shared/services/utils.service";
import {NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {TranslateModule} from "@ngx-translate/core";
import {PaginatedInterfaceComponent} from "@app/shared/components/paginated-interface/paginated-interface.component";

@Component({
    changeDetection: ChangeDetectionStrategy.OnPush,
    selector: "src-auditlog-tab2",
    templateUrl: "./audit-log-tab2.component.html",
    standalone: true,
    imports: [DatePipe, NgbTooltipModule, PaginatedInterfaceComponent, TranslateModule]
})
export class AuditLogTab2Component {
  private utilsService = inject(UtilsService);
  protected usersResolver = inject(UsersResolver);

  readonly users = computed(() => this.usersResolver.resource.value());

  exportAuditLog() {
    this.utilsService.generateCSV('users', this.users());
  }
}
