import {Component, Input, OnInit, inject} from "@angular/core";
import {HttpClient} from "@angular/common/http";
import {NgbActiveModal} from "@ng-bootstrap/ng-bootstrap";
import {TranslateModule} from "@ngx-translate/core";
import {WbtipService} from "@app/services/helper/wbtip.service";
import {Comment} from "@app/models/app/shared-public-model";
import {WbForward} from "@app/models/receiver/receiver-tip-data";
import {TipCommentsComponent} from "@app/shared/partials/tip-comments/tip-comments.component";

@Component({
    selector: "src-wb-forward-messages",
    templateUrl: "./wb-forward-messages.component.html",
    standalone: true,
    imports: [TipCommentsComponent, TranslateModule]
})
export class WbForwardMessagesComponent implements OnInit {
  protected activeModal = inject(NgbActiveModal);
  private http = inject(HttpClient);
  protected wbTipService = inject(WbtipService);

  @Input() forward: WbForward;

  messages: Comment[] = [];

  ngOnInit(): void {
    this.http.get<Comment[]>(`api/whistleblower/wbtip/forwards/${this.forward.id}/messages`).subscribe({
      next: (messages) => {
        this.messages = messages;
      },
      error: () => {}
    });
  }
}
