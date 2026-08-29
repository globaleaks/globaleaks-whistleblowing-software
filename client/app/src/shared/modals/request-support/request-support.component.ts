import {CollapsibleCardComponent} from "@app/shared/components/collapsible-card/collapsible-card.component";
import {DatePipe, NgClass, NgTemplateOutlet} from "@angular/common";
import {ChangeDetectorRef, Component, OnInit, inject} from "@angular/core";
import {NgbActiveModal, NgbNavModule} from "@ng-bootstrap/ng-bootstrap";
import {PreferenceResolver} from "@app/shared/resolvers/preference.resolver";
import {Constants} from "@app/shared/constants/constants";
import {FormsModule} from "@angular/forms";

import {TranslateModule} from "@ngx-translate/core";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {AppDataService} from "@app/app-data.service";
import {HttpService} from "@app/shared/services/http.service";
import {appendSupportMessage, NewSupportRequest, supportRequestStatusClass, supportRequestStatusLabels, SupportRequest} from "@app/models/app/support";
import {SupportThreadComponent} from "@app/shared/partials/support-thread/support-thread.component";

@Component({
    selector: "src-request-support",
    templateUrl: "./request-support.component.html",
    standalone: true,
    imports: [CollapsibleCardComponent, DatePipe, FormsModule, NgbNavModule, NgClass, NgTemplateOutlet, SupportThreadComponent, TranslateModule]
})
export class RequestSupportComponent implements OnInit {
  protected activeModal = inject(NgbActiveModal);
  protected authenticationService = inject(AuthenticationService);
  private appDataService = inject(AppDataService);
  private httpService = inject(HttpService);
  private preferenceResolver = inject(PreferenceResolver);
  private changeDetectorRef = inject(ChangeDetectorRef);

  protected readonly Constants = Constants;
  markingReadIds = new Set<string>();
  requestsLoaded = false;
  activeTab = "requests";
  expandedRequestId = "";
  arg: { mail_address: string, text: string } = {mail_address: "", text: ""};
  requests: SupportRequest[] = [];
  replyDrafts: Record<string, string> = {};

  readonly statusLabels = supportRequestStatusLabels;
  readonly statusClass = supportRequestStatusClass;

  ngOnInit(): void {
    this.arg.mail_address = this.preferenceResolver.dataModel?.mail_address || "";

    // Whoever can read its own threads opens support mostly to read the reply
    // it has been notified of, and the requests are what it is looking for;
    // whoever cannot opens it from the login and writes at once.
    if (this.canReadRequests) {
      this.loadRequests();
    }
  }

  /**
   * With threads to read the modal is a two tab interface, the existing
   * requests and a new one; with none there is nothing to choose between, so
   * the form is presented alone. Whoever cannot read its own threads writes at
   * once: it opens support from the login and has no list to be offered.
   */
  get showTabs(): boolean {
    return this.canReadRequests && this.requestsLoaded && this.requests.length > 0;
  }

  get showForm(): boolean {
    return !this.canReadRequests || (this.requestsLoaded && !this.requests.length);
  }

  /**
   * The request is attributed to its author, so no address is asked: either a
   * session identifies it, or the identity it has authenticated on the
   * identity provider is bound to its account and identifies it just the same.
   */
  get authenticated(): boolean {
    const session = this.authenticationService.session;
    return !!session && session.role !== "whistleblower";
  }

  /**
   * The threads of the requester are readable only by a session that has
   * completed its access: an user that is being asked for its password reaches
   * the platform limited to that step, and one identified by the identity
   * provider alone holds no session at all. There support is opened to write,
   * not to read.
   */
  get canReadRequests(): boolean {
    const session = this.authenticationService.session;
    return !!session && session.role !== "whistleblower" &&
      !this.preferenceResolver.dataModel?.password_change_needed &&
      !this.preferenceResolver.dataModel?.require_two_factor;
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

    // The request is submitted with the proof of work required of whoever
    // holds no session, which replaces the headers of the request: the
    // identity authenticated on the identity provider is passed explicitly so
    // that it reaches the backend, which attributes the request to its account
    this.httpService.requestSupport(request, this.authenticationService.getHeader()).subscribe({
      next: () => {
        this.arg.text = "";
        if (this.canReadRequests) {
          // The request just written is the first thing to show: the list of
          // the requests is where it now lives
          this.activeTab = "requests";
          this.changeDetectorRef.detectChanges();
          this.loadRequests();
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

  loadRequests(): void {
    if (!this.supportAvailable || !this.canReadRequests) {
      return;
    }

    this.httpService.requestUserSupport().subscribe({
      next: (requests) => {
        this.requests = requests.map(request => ({...request, messages: request.messages || []}));
        this.requestsLoaded = true;
        this.changeDetectorRef.detectChanges();
      },
      error: () => {
        this.requestsLoaded = true;
        this.changeDetectorRef.detectChanges();
      }
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
          this.changeDetectorRef.detectChanges();
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

  sendFollowup(request: SupportRequest, content: string): void {
    this.httpService.requestUserSupportMessage(request.id, {content}).subscribe({
      next: (message) => {
        appendSupportMessage(request, message, request.status);
        this.requests = [request, ...this.requests.filter(item => item.id !== request.id)];
        this.replyDrafts[request.id] = "";
        this.changeDetectorRef.detectChanges();
      },
      error: () => {}
    });
  }

}
