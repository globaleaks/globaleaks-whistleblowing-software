import {DatePipe, NgClass} from "@angular/common";
import {Component, OnInit, inject} from "@angular/core";
import {FormsModule} from "@angular/forms";
import {supportRequestStatusClass, supportRequestStatusLabels, supportRequestStatuses, SupportMessage, SupportRequest, SupportRequestStatus} from "@app/models/app/support";
import {tenantResolverModel} from "@app/models/resolvers/tenant-resolver-model";
import {DeleteConfirmationComponent} from "@app/shared/modals/delete-confirmation/delete-confirmation.component";
import {PaginatedInterfaceComponent} from "@app/shared/components/paginated-interface/paginated-interface.component";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {HttpService} from "@app/shared/services/http.service";
import {NgbModal} from "@ng-bootstrap/ng-bootstrap";
import {TranslateModule} from "@ngx-translate/core";

@Component({
  selector: "src-admin-support",
  templateUrl: "./support.component.html",
  standalone: true,
  imports: [DatePipe, FormsModule, NgClass, PaginatedInterfaceComponent, TranslateModule, TranslatorPipe]
})
export class AdminSupportComponent implements OnInit {
  private httpService = inject(HttpService);
  private modalService = inject(NgbModal);
  private nodeResolver = inject(NodeResolver);

  requests: SupportRequest[] = [];
  filteredRequests: SupportRequest[] = [];
  expandedRequestId = "";
  replyDrafts: Record<string, string> = {};
  selectedTenantId = 0;
  availableTenants: tenantResolverModel[] = [];

  readonly statuses = supportRequestStatuses;
  readonly statusLabels = supportRequestStatusLabels;
  readonly statusClass = supportRequestStatusClass;

  ngOnInit(): void {
    this.loadRequests();
    if (this.nodeResolver.dataModel.root_tenant) {
      this.httpService.fetchTenant().subscribe({
        next: tenants => {
          this.availableTenants = tenants
            .filter(tenant => tenant.id < 1000001)
            .sort((a, b) => a.id - b.id);
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
          messages: request.messages || []
        }));
        this.applyFilters();
      },
      error: () => {}
    });
  }

  statusLabel(status: SupportRequestStatus): string {
    return this.statusLabels[status];
  }

  applyFilters(): void {
    this.filteredRequests = this.selectedTenantId ?
      this.requests.filter(request => request.tid === this.selectedTenantId) :
      [...this.requests];
  }

  get tenants(): {id: number; name: string}[] {
    if (this.availableTenants.length) {
      return this.availableTenants.map(({id, name}) => ({id, name}));
    }

    const tenants = new Map<number, string>();
    for (const request of this.requests) {
      tenants.set(request.tid, request.tenant_name);
    }

    return Array.from(tenants, ([id, name]) => ({id, name}))
      .sort((a, b) => a.id - b.id);
  }

  toggleRequest(request: SupportRequest): void {
    if (this.expandedRequestId === request.id) {
      this.expandedRequestId = "";
      return;
    }

    this.expandedRequestId = request.id;
    if (request.status === "new" && this.canDecrypt(request)) {
      this.updateStatus(request, "read");
    }
  }

  updateStatus(request: SupportRequest, status: SupportRequestStatus): void {
    if (request.status === status) {
      return;
    }

    this.httpService.requestUpdateAdminSupport(request.id, {status}).subscribe(updated => {
      const messages = request.messages;
      Object.assign(request, updated || {status});
      request.messages = updated?.messages || messages;
      this.applyFilters();
    });
  }

  sendReply(request: SupportRequest): void {
    const content = (this.replyDrafts[request.id] || "").trim();
    if (!content || !this.canDecrypt(request)) {
      return;
    }

    this.httpService.requestAdminSupportMessage(request.id, {content}).subscribe({
      next: (message) => {
        request.messages = [...request.messages, message];
        request.message_count = request.messages.length;
        request.preview = message.content;
        request.update_date = message.creation_date;
        request.status = "answered";
        this.applyFilters();
        this.replyDrafts[request.id] = "";
      },
      error: () => {}
    });
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
        this.applyFilters();
      });
    };
  }

  canDecrypt(request: SupportRequest): boolean {
    return request.key_available;
  }

  preview(request: SupportRequest): string {
    if (request.preview) {
      return request.preview;
    }

    return [...request.messages].reverse().find(message => message.content)?.content || "";
  }

  messageAuthor(request: SupportRequest, message: SupportMessage): string {
    if (message.author_id) {
      return "Admin";
    }

    return request.author_id ? "User" : "Anonymous";
  }

}
