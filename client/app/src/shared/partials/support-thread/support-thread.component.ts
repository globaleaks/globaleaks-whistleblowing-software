import {DatePipe} from "@angular/common";
import {Component, EventEmitter, Input, Output, inject} from "@angular/core";
import {FormsModule} from "@angular/forms";
import {SupportMessage, SupportRequest} from "@app/models/app/support";
import {TranslateModule, TranslateService} from "@ngx-translate/core";

/**
 * The conversation of a support request: the messages from the oldest to the
 * newest and the box to answer.
 *
 * The thread is the same on both sides of the conversation; what changes is
 * who the reader is, and the notice shown above the answer box, which the
 * caller projects.
 */
@Component({
  selector: "src-support-thread",
  templateUrl: "./support-thread.component.html",
  standalone: true,
  imports: [DatePipe, FormsModule, TranslateModule]
})
export class SupportThreadComponent {
  private readonly translateService = inject(TranslateService);

  @Input() request!: SupportRequest;
  @Input() viewer: "admin" | "user" = "user";
  @Input() draft = "";
  @Output() draftChange = new EventEmitter<string>();
  @Output() send = new EventEmitter<string>();

  get canReply(): boolean {
    return this.request.key_available && this.request.status !== "closed";
  }

  messageAuthor(message: SupportMessage): string {
    if (message.author_id) {
      return this.translateService.instant("Admin");
    }

    if (this.viewer === "user") {
      return this.translateService.instant("You");
    }

    return this.request.author_username || this.translateService.instant("Anonymous");
  }

  onDraftChange(draft: string): void {
    this.draft = draft;
    this.draftChange.emit(draft);
  }

  sendMessage(): void {
    const content = (this.draft || "").trim();
    if (content && this.canReply) {
      this.send.emit(content);
    }
  }
}
