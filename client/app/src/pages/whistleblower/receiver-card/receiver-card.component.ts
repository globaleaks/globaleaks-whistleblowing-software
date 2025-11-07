import {Component, Input, inject} from "@angular/core";
import {Receiver} from "@app/models/app/public-model";
import {SubmissionService} from "@app/services/helper/submission.service";
import {TranslateService} from "@ngx-translate/core";
import {NgClass} from "@angular/common";
import {FormsModule} from "@angular/forms";
import {MarkdownComponent} from "ngx-markdown";
import {StripHtmlPipe} from "@app/shared/pipes/strip-html.pipe";

@Component({
    selector: "src-receiver-card",
    templateUrl: "./receiver-card.component.html",
    standalone: true,
    imports: [FormsModule, MarkdownComponent, NgClass, StripHtmlPipe]
})
export class ReceiverCardComponent {
  protected translate = inject(TranslateService);

  @Input() submission: SubmissionService;
  @Input() receiverModel: Receiver;

  selectable(): boolean {
    if (this.submission.context.maximum_selectable_receivers === 0) {
      return true;
    }

    return Object.keys(this.submission.selected_receivers).length < this.submission.context.maximum_selectable_receivers;
  }

  switchSelection(receiver: Receiver): void {
    if (receiver.forcefully_selected) {
      return;
    }

    if (!this.submission.selected_receivers[receiver.id]) {
      delete this.submission.selected_receivers[receiver.id];
    } else if (this.selectable()) {
      this.submission.selected_receivers[receiver.id] = true;
    }
  }
}
