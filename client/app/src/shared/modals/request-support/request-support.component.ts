import {DatePipe, NgClass} from "@angular/common";
import {ChangeDetectorRef, Component, OnInit, inject} from "@angular/core";
import {NgbActiveModal} from "@ng-bootstrap/ng-bootstrap";
import {UtilsService} from "@app/shared/services/utils.service";
import {PreferenceResolver} from "@app/shared/resolvers/preference.resolver";
import {Constants} from "@app/shared/constants/constants";
import {FormsModule} from "@angular/forms";

import {TranslateModule} from "@ngx-translate/core";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {AppDataService} from "@app/app-data.service";
import {HttpService} from "@app/shared/services/http.service";
import {NewSupportRequest, supportRequestStatusClass, supportRequestStatusLabels, SupportMessage, SupportRequest} from "@app/models/app/support";

@Component({
    selector: "src-request-support",
    templateUrl: "./request-support.component.html",
    standalone: true,
    imports: [DatePipe, FormsModule, NgClass, TranslateModule, TranslatorPipe]
})
export class RequestSupportComponent implements OnInit {
  protected activeModal = inject(NgbActiveModal);
  protected utilsService = inject(UtilsService);
  protected authenticationService = inject(AuthenticationService);
  private appDataService = inject(AppDataService);
  private httpService = inject(HttpService);
  private preferenceResolver = inject(PreferenceResolver);
  private changeDetectorRef = inject(ChangeDetectorRef);

  protected readonly Constants = Constants;
  markingReadIds = new Set<string>();
  view: "new" | "requests" = "new";
  expandedRequestId = "";
  arg: { mail_address: string, text: string } = {mail_address: "", text: ""};
  requests: SupportRequest[] = [];
  replyDrafts: Record<string, string> = {};

  readonly statusLabels = supportRequestStatusLabels;
  readonly statusClass = supportRequestStatusClass;

  ngOnInit(): void {
    this.arg.mail_address = this.preferenceResolver.dataModel?.mail_address || "";
  }

  get authenticated(): boolean {
    const session = this.authenticationService.session;
    return !!session && session.role !== "whistleblower";
  }

  get supportAvailable(): boolean {
    const session = this.authenticationService.session;
    return !!this.appDataService.public?.node?.support &&
      !session?.properties?.management_session;
  }

  submitRequest(): void {
    if (!this.supportAvailable || !this.isRequestValid()) {
      return;
    }

    const request: NewSupportRequest = {text: this.arg.text};
    if (!this.authenticated) {
      request.mail_address = this.arg.mail_address;
    }

    this.utilsService.submitSupportRequest(request).subscribe({
      next: () => {
        this.arg.text = "";
        if (this.authenticated) {
          this.showRequests();
        } else {
          this.activeModal.close();
        }
      },
      error: () => {}
    });
  }

  isRequestValid(): boolean {
    const validEmail = this.authenticated || new RegExp(Constants.emailRegexp).test(this.arg.mail_address || "");
    return validEmail && !!this.arg.text.trim();
  }

  startNewRequest(): void {
    this.view = "new";
  }

  showRequests(): void {
    this.view = "requests";
    this.loadRequests();
    this.changeDetectorRef.detectChanges();
  }

  loadRequests(): void {
    if (!this.supportAvailable || !this.authenticated) {
      return;
    }

    this.httpService.requestUserSupport().subscribe({
      next: (requests) => {
        this.requests = requests.map(request => ({...request, messages: request.messages || []}));
        this.changeDetectorRef.detectChanges();
      },
      error: () => {}
    });
  }

  toggleRequest(request: SupportRequest): void {
    const expanding = this.expandedRequestId !== request.id;
    this.expandedRequestId = expanding ? request.id : "";

    if (expanding && this.hasUnreadAdminMessages(request) && !this.markingReadIds.has(request.id)) {
      this.markingReadIds.add(request.id);
      this.httpService.requestUpdateUserSupport(request.id).subscribe({
        next: () => {
          request.messages = request.messages.map(message =>
            message.author_id && message.new ? {...message, new: false} : message
          );
          this.markingReadIds.delete(request.id);
        },
        error: () => {
          this.markingReadIds.delete(request.id);
        }
      });
    }
  }

  hasUnreadAdminMessages(request: SupportRequest): boolean {
    return request.messages.some(message => !!message.author_id && message.new);
  }

  sendFollowup(request: SupportRequest): void {
    const content = (this.replyDrafts[request.id] || "").trim();
    if (!content || !this.canDecrypt(request) || request.status === "closed") {
      return;
    }

    this.httpService.requestUserSupportMessage(request.id, {content}).subscribe({
      next: (message) => {
        request.messages = [...request.messages, message];
        request.message_count = request.messages.length;
        request.preview = message.content;
        request.update_date = message.creation_date;
        request.status = "new";
        this.requests = [request, ...this.requests.filter(item => item.id !== request.id)];
        this.replyDrafts[request.id] = "";
      },
      error: () => {}
    });
  }

  canDecrypt(request: SupportRequest): boolean {
    return request.key_available;
  }

  messageAuthor(message: SupportMessage): string {
    return message.author_id ? "Admin" : "You";
  }

}
