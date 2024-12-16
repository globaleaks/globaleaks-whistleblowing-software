import {Component, OnInit, inject} from "@angular/core";
import {UsersResolver} from "@app/shared/resolvers/users.resolver";
import {User} from "@app/models/resolvers/user-resolver-model";
import {UtilsService} from "@app/shared/services/utils.service";
import {NgClass, DatePipe} from "@angular/common";
import {NgbPagination, NgbPaginationPrevious, NgbPaginationNext, NgbPaginationFirst, NgbPaginationLast, NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {TranslateModule} from "@ngx-translate/core";

@Component({
    selector: "src-auditlog-tab2",
    templateUrl: "./audit-log-tab2.component.html",
    standalone: true,
    imports: [NgClass, NgbPagination, NgbPaginationPrevious, NgbPaginationNext, NgbPaginationFirst, NgbPaginationLast, NgbTooltipModule, DatePipe, TranslatorPipe, TranslateModule]
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
    this.users = this.usersResolver.dataModel.users;
  }

  getPaginatedData(): User[] {
    const startIndex = (this.currentPage - 1) * this.pageSize;
    const endIndex = startIndex + this.pageSize;
    return this.users.slice(startIndex, endIndex);
  }

  exportAuditLog() {
    this.utilsService.generateCSV(JSON.stringify(this.users), 'users', ["id", "creation_date", "username", "salt", "role", "enabled", "last_login", "name", "description", "public_name", "mail_address", "change_email_address", "language", "password_change_needed", "password_change_date", "pgp_key_fingerprint", "pgp_key_public", "pgp_key_expiration", "pgp_key_remove", "picture", "tid", "notification", "encryption", "escrow", "two_factor", "forcefully_selected", "can_postpone_expiration", "can_delete_submission", "can_grant_access_to_reports", "can_transfer_access_to_reports", "can_edit_general_settings", "clicked_recovery_key", "accepted_privacy_policy", "contexts"]);
  }
}
