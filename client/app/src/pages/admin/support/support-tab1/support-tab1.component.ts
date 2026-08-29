import {DatePipe, NgClass} from "@angular/common";
import {Component, OnInit, inject} from "@angular/core";
import {FormsModule} from "@angular/forms";
import {ActivatedRoute, RouterLink} from "@angular/router";
import {appendSupportMessage, supportRequestStatusClass, supportRequestStatusLabels, supportRequestStatuses, SupportRequest, SupportRequestStatus} from "@app/models/app/support";
import {tenantResolverModel} from "@app/models/resolvers/tenant-resolver-model";
import {DeleteConfirmationComponent} from "@app/shared/modals/delete-confirmation/delete-confirmation.component";
import {PaginatedInterfaceComponent} from "@app/shared/components/paginated-interface/paginated-interface.component";
import {TableHeaderComponent} from "@app/shared/components/table/table-header.component";
import {TableFilterOption, TableState} from "@app/shared/components/table/table-state";
import {SupportThreadComponent} from "@app/shared/partials/support-thread/support-thread.component";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {PreferenceResolver} from "@app/shared/resolvers/preference.resolver";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {HttpService} from "@app/shared/services/http.service";
import {UtilsService} from "@app/shared/services/utils.service";
import {NgbModal, NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {TranslateModule, TranslateService} from "@ngx-translate/core";

/**
 * The status is sorted along the lifecycle of the request (new, read,
 * opened, closed) and not alphabetically: the rank is kept on the row so
 * that the sorting stays the one of the paginated interface.
 */
interface SupportRequestRow extends SupportRequest {
  status_order: number;
}

@Component({
  selector: "src-support-tab1",
  templateUrl: "./support-tab1.component.html",
  standalone: true,
  imports: [DatePipe, FormsModule, NgbTooltipModule, NgClass, PaginatedInterfaceComponent, RouterLink, SupportThreadComponent, TableHeaderComponent, TranslateModule]
})
export class SupportTab1Component implements OnInit {
  private httpService = inject(HttpService);
  private modalService = inject(NgbModal);
  private translateService = inject(TranslateService);
  private utilsService = inject(UtilsService);
  private authenticationService = inject(AuthenticationService);
  private preferenceResolver = inject(PreferenceResolver);
  private activatedRoute = inject(ActivatedRoute);
  protected nodeResolver = inject(NodeResolver);

  requests: SupportRequestRow[] = [];
  expandedRequestId = "";
  // The notification of a request links to it: the list opens with its card
  // expanded, so that the mail lands on the request it announces
  private focusRequestId = "";
  replyDrafts: Record<string, string> = {};
  availableTenants: tenantResolverModel[] = [];

  tenantOptions: TableFilterOption[] = [];
  userOptions: TableFilterOption[] = [];
  statusOptions: TableFilterOption[] = [];

  readonly statuses = supportRequestStatuses;
  readonly statusLabels = supportRequestStatusLabels;
  readonly statusClass = supportRequestStatusClass;

  readonly table = new TableState<SupportRequestRow>({
    orderBy: "update_date",
    orderDesc: true,
    filters: {
      tid: {type: "select"},
      creation_date: {type: "daterange"},
      update_date: {type: "daterange"},
      author_username: {type: "select"},
      status: {type: "select"}
    }
  });

  ngOnInit(): void {
    this.statusOptions = this.statuses.map(status => ({id: status, label: this.translateService.instant(this.statusLabels[status])}));
    this.loadRequests();

    this.activatedRoute.queryParams.subscribe(params => {
      this.focusRequestId = params["id"] || "";
      this.focusRequest();
    });

    if (this.nodeResolver.dataModel.root_tenant) {
      this.httpService.fetchTenant().subscribe({
        next: tenants => {
          this.availableTenants = tenants
            .filter(tenant => tenant.id < 1000001)
            .sort((a, b) => a.id - b.id);
          this.updateTenantOptions();
        },
        error: () => {}
      });
    }
  }

  loadRequests(): void {
    this.httpService.requestAdminSupport().subscribe({
      next: (requests) => {
        this.requests = requests.map(request => ({
          ...request,
          messages: request.messages || [],
          status_order: this.statuses.indexOf(request.status)
        }));
        this.updateTenantOptions();
        this.updateUserOptions();
        this.table.setItems(this.requests);
        this.focusRequest();
      },
      error: () => {}
    });
  }

  /**
   * The author of a request and the site it comes from are read where they are
   * configured: the administrative pages of the users and of the sites, which
   * are offered only to whom holds the permission on that area. An author that
   * is not authenticated has no account to reach.
   *
   * The account of another tenant is configured on that tenant: it is reached
   * by whom may also enter the sites, through the same switch the sites page
   * performs.
   */
  canReachAuthor(request: SupportRequest): boolean {
    return !!request.author_id &&
      !!this.permissions.can_manage_users &&
      (this.isLocalAuthor(request) || this.canReachTenant());
  }

  isLocalAuthor(request: SupportRequest): boolean {
    return request.tid === this.nodeResolver.dataModel.tid;
  }

  /**
   * Open the page of an author belonging to another tenant: the administration
   * of that tenant is entered aside, as the sites page does, and lands on the
   * card of the account.
   */
  openAuthor(request: SupportRequest): void {
    const target = "/admin/users?id=" + request.author_id;

    this.httpService.requestTenantSwitch("api/auth/tenantauthswitch/" + request.tid).subscribe(response => {
      if (response.redirect) {
        window.open(response.redirect + "&redirect=" + encodeURIComponent(target), "_blank", "noopener");
      }
    });
  }

  canReachTenant(): boolean {
    return this.nodeResolver.dataModel.root_tenant && !!this.permissions.can_manage_sites;
  }

  private get permissions() {
    return this.preferenceResolver.dataModel.profile.permissions;
  }

  get columnCount(): number {
    return this.nodeResolver.dataModel.root_tenant ? 7 : 6;
  }

  statusLabel(status: SupportRequestStatus): string {
    return this.statusLabels[status];
  }

  updateTenantOptions(): void {
    const tenants = new Map<number, string>();

    for (const tenant of this.availableTenants) {
      tenants.set(tenant.id, tenant.name);
    }

    for (const request of this.requests) {
      if (!tenants.has(request.tid)) {
        tenants.set(request.tid, request.tenant_name);
      }
    }

    this.tenantOptions = Array.from(tenants, ([id, name]) => ({id, label: name || String(id)}))
      .sort((a, b) => (a.id as number) - (b.id as number));
  }

  updateUserOptions(): void {
    const usernames = new Set<string>();

    for (const request of this.requests) {
      if (request.author_username) {
        usernames.add(request.author_username);
      }
    }

    this.userOptions = Array.from(usernames)
      .sort((a, b) => a.localeCompare(b))
      .map(username => ({id: username, label: username}));
  }

  /**
   * Whether the requester wrote something the administrators have not read
   * yet: it is what marks the row of a request that awaits attention, as an
   * updated report does in the list of the recipients.
   */
  hasUnreadUserMessages(request: SupportRequestRow): boolean {
    return (request.messages || []).some(message => !message.author_id && message.new);
  }

  private focusRequest(): void {
    if (!this.focusRequestId || this.expandedRequestId === this.focusRequestId) {
      return;
    }

    const request = this.requests.find(item => item.id === this.focusRequestId);
    if (request) {
      this.toggleRequest(request);
    }
  }

  /**
   * The row is the handle of the request it displays: a click anywhere on it
   * opens the request, save for the elements that already carry an action of
   * their own - the links towards the site and the author, the buttons - which
   * are left to it.
   */
  onRowClick(request: SupportRequestRow, event: MouseEvent): void {
    const target = event.target as HTMLElement | null;

    if (target && target.closest("a, button, input, select, textarea, label")) {
      return;
    }

    this.toggleRequest(request);
  }

  toggleRequest(request: SupportRequestRow): void {
    if (this.expandedRequestId === request.id) {
      this.expandedRequestId = "";
      return;
    }

    this.expandedRequestId = request.id;
    if (request.status === "new" && request.key_available) {
      this.updateStatus(request, "opened");
    } else if (this.hasUnreadUserMessages(request) && request.key_available) {
      this.markRead(request);
    }
  }

  /**
   * A request already opened that receives a follow-up is read by expanding it:
   * the status does not change and neither does the update date, only the
   * messages stop being new.
   */
  markRead(request: SupportRequestRow): void {
    this.httpService.requestReadAdminSupport(request.id).subscribe({
      next: () => {
        request.messages = (request.messages || []).map(message =>
          !message.author_id && message.new ? {...message, new: false} : message
        );
      },
      error: () => {}
    });
  }

  updateStatus(request: SupportRequestRow, status: SupportRequestStatus): void {
    if (request.status === status) {
      return;
    }

    this.httpService.requestUpdateAdminSupport(request.id, {status}).subscribe(updated => {
      const messages = request.messages;
      Object.assign(request, updated || {status});
      request.messages = updated?.messages || messages;
      request.status_order = this.statuses.indexOf(request.status);
      this.table.refresh();
    });
  }

  sendReply(request: SupportRequestRow, content: string): void {
    this.httpService.requestAdminSupportMessage(request.id, {content}).subscribe({
      next: (message) => {
        appendSupportMessage(request, message, "opened");
        request.status_order = this.statuses.indexOf(request.status);
        this.table.refresh();
        this.replyDrafts[request.id] = "";
      },
      error: () => {}
    });
  }

  /**
   * An user that has lost its password asks for support to regain its access:
   * the reset link is sent from here, so that the administrator answers where
   * the request is instead of looking the account up in the users page.
   *
   * The conditions are the ones of the users page: it is the key escrow that
   * lets an administrator restore the access to an encrypted account, so the
   * platform must have it enabled and the administrator must hold the key. The
   * link is offered only for the requests of an identified author, only for
   * the accounts of the tenant being operated - the operation is performed on
   * that tenant - and never on the account of the administrator itself, which
   * the backend refuses.
   */
  canResetAuthorPassword(request: SupportRequest): boolean {
    return !!request.author_id &&
      request.author_id !== this.authenticationService.session?.user_id &&
      request.tid === this.nodeResolver.dataModel.tid &&
      this.nodeResolver.dataModel.escrow &&
      this.preferenceResolver.dataModel.escrow;
  }

  resetAuthorPassword(request: SupportRequest): void {
    // Nothing of what is displayed changes, so the thread being read is left
    // open instead of being reloaded
    this.utilsService.runAdminOperation("send_password_reset_email", {"value": request.author_id}, false).subscribe();
  }

  deleteRequest(request: SupportRequest): void {
    const modalRef = this.modalService.open(DeleteConfirmationComponent, {
      backdrop: "static",
      keyboard: false,
      ariaLabelledBy: "modal-title"
    });
    modalRef.componentInstance.confirmFunction = () => {
      this.httpService.requestDeleteAdminSupport(request.id).subscribe(() => {
        this.requests = this.requests.filter(item => item.id !== request.id);
        if (this.expandedRequestId === request.id) {
          this.expandedRequestId = "";
        }
        this.updateUserOptions();
        this.table.setItems(this.requests);
      });
    };
  }
}
