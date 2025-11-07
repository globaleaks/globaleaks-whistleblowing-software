import {Component, OnInit, inject} from "@angular/core";
import {UsersResolver} from "@app/shared/resolvers/users.resolver";
import {User} from "@app/models/resolvers/user-resolver-model";
import {UtilsService} from "@app/shared/services/utils.service";
import {DatePipe} from "@angular/common";
import {NgbPagination, NgbPaginationPrevious, NgbPaginationNext, NgbPaginationFirst, NgbPaginationLast, NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {TranslateModule} from "@ngx-translate/core";

@Component({
    selector: "src-auditlog-tab2",
    templateUrl: "./audit-log-tab2.component.html",
    standalone: true,
    imports: [NgbPagination, NgbPaginationPrevious, NgbPaginationNext, NgbPaginationFirst, NgbPaginationLast, NgbTooltipModule, DatePipe, TranslatorPipe, TranslateModule]
})
export class AuditLogTab2Component implements OnInit{
  private utilsService = inject(UtilsService);
  protected usersResolver = inject(UsersResolver);

  currentPage = 1;
  pageSize = 20;
  users: User[] = [];

  ngOnInit() {
    this.loadAuditLogData();
  }

  loadAuditLogData() {
    this.users = this.usersResolver.dataModel;
  }

  getPaginatedData(): User[] {
    const startIndex = (this.currentPage - 1) * this.pageSize;
    const endIndex = startIndex + this.pageSize;
    return this.users.slice(startIndex, endIndex);
  }

  exportAuditLog() {
    this.utilsService.generateCSV('users', this.users);
  }
}
