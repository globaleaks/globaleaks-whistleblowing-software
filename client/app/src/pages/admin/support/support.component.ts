import {DatePipe, NgClass} from "@angular/common";
import {Component, OnInit, inject} from "@angular/core";
import {FormsModule} from "@angular/forms";
import {
  SupportMessage,
  SupportRequest,
  SupportRequestStatus
} from "@app/models/app/support";
import {DeleteConfirmationComponent} from "@app/shared/modals/delete-confirmation/delete-confirmation.component";
import {PaginatedInterfaceComponent} from "@app/shared/components/paginated-interface/paginated-interface.component";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {HttpService} from "@app/shared/services/http.service";
import {UtilsService} from "@app/shared/services/utils.service";
import {NgbModal} from "@ng-bootstrap/ng-bootstrap";
import {TranslateModule} from "@ngx-translate/core";
import {AppDataService} from "@app/app-data.service";
import {AuthenticationService} from "@app/services/helper/authentication.service";

@Component({
  selector: "src-admin-support",
  templateUrl: "./support.component.html",
  standalone: true,
  imports: [DatePipe, FormsModule, NgClass, PaginatedInterfaceComponent, TranslateModule, TranslatorPipe]
})
export class AdminSupportComponent implements OnInit {
  private appDataService = inject(AppDataService);
  private authenticationService = inject(AuthenticationService);
  private httpService = inject(HttpService);
  private modalService = inject(NgbModal);
  private utilsService = inject(UtilsService);
  protected nodeResolver = inject(NodeResolver);

  requests: SupportRequest[] = [];
  filteredRequests: SupportRequest[] = [];
  expandedRequestId = "";
  statusFilter: SupportRequestStatus | "all" = "all";
  searchTerm = "";
  replyDrafts: Record<string, string> = {};
  initializing = false;
  sendingReplyId = "";

  readonly statuses: SupportRequestStatus[] = ["new", "read", "answered", "closed"];
  readonly statusLabels: Record<SupportRequestStatus, string> = {
    new: "New",
    read: "Read",
    answered: "Answered",
    closed: "Closed"
  };

  ngOnInit(): void {
    if (this.nodeResolver.dataModel.support) {
      this.loadRequests();
    }
  }

  get managementSession(): boolean {
    return !!this.authenticationService.session?.properties?.management_session;
  }

  initializeSupport(): void {
    if (this.managementSession || this.initializing || !this.nodeResolver.dataModel.encryption) {
      return;
    }

    this.initializing = true;
    this.utilsService.runAdminOperation("initialize_support", {}, false).subscribe({
      next: () => {
        this.nodeResolver.dataModel.support = true;
        this.appDataService.public.node.support = true;
        this.initializing = false;
        this.loadRequests();
      },
      error: () => {
        this.initializing = false;
      }
    });
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
      error: () => { }
    });
  }

  statusLabel(status: SupportRequestStatus): string {
    return this.statusLabels[status] || status;
  }

  applyFilters(): void {
    const statusFiltered = this.statusFilter === "all"
      ? [...this.requests]
      : this.requests.filter(request => request.status === this.statusFilter);

    const searchTerm = this.searchTerm.trim().toLocaleLowerCase();
    this.filteredRequests = searchTerm
      ? statusFiltered.filter(request => {
          const searchableContent = [
            request.id,
            request.mail_address,
            request.preview,
            ...request.messages.map(message => message.content)
          ].join("\n").toLocaleLowerCase();

          return searchableContent.includes(searchTerm);
        })
      : statusFiltered;
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
    if (!content || this.sendingReplyId || !this.canDecrypt(request)) {
      return;
    }

    this.sendingReplyId = request.id;
    this.httpService.requestAdminSupportMessage(request.id, {content}).subscribe({
      next: (message) => {
        request.messages = [...request.messages, message];
        request.message_count = request.messages.length;
        request.preview = message.content;
        request.update_date = message.creation_date;
        request.status = "answered";
        this.applyFilters();
        this.replyDrafts[request.id] = "";
        this.sendingReplyId = "";
      },
      error: () => {
        this.sendingReplyId = "";
      }
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
    return request.decryptable !== false && request.key_available !== false;
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

  statusClass(status: SupportRequestStatus): string {
    switch (status) {
      case "new":
        return "bg-info";
      case "read":
        return "bg-secondary";
      case "answered":
        return "bg-success";
      case "closed":
        return "bg-dark";
      default:
        return "bg-secondary";
    }
  }
}
