import {Component, OnInit, inject} from "@angular/core";
import {DatePipe} from "@angular/common";
import {UsersResolver} from "@app/shared/resolvers/users.resolver";
import {User} from "@app/models/resolvers/user-resolver-model";
import {UtilsService} from "@app/shared/services/utils.service";
import {NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {TranslateModule} from "@ngx-translate/core";
import {PaginatedInterfaceComponent} from "@app/shared/components/paginated-interface/paginated-interface.component";

@Component({
    selector: "src-auditlog-tab2",
    templateUrl: "./audit-log-tab2.component.html",
    standalone: true,
    imports: [DatePipe, NgbTooltipModule, PaginatedInterfaceComponent, TranslatorPipe, TranslateModule]
})
export class AuditLogTab2Component implements OnInit{
  private utilsService = inject(UtilsService);
  protected usersResolver = inject(UsersResolver);

  users: User[] = [];

  ngOnInit() {
    this.loadAuditLogData();
  }

  loadAuditLogData() {
    this.users = this.usersResolver.dataModel;
  }

  exportAuditLog() {
    this.utilsService.generateCSV('users', this.users);
  }
}
