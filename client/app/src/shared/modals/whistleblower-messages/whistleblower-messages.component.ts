import {Component, Input, inject} from "@angular/core";
import {NgbActiveModal} from "@ng-bootstrap/ng-bootstrap";
import {TranslateModule} from "@ngx-translate/core";
import {ReceiverTipService} from "@app/services/helper/receiver-tip.service";
import {TipCommentsComponent} from "@app/shared/partials/tip-comments/tip-comments.component";

@Component({
    selector: "src-whistleblower-messages",
    templateUrl: "./whistleblower-messages.component.html",
    standalone: true,
    imports: [TipCommentsComponent, TranslateModule]
})
export class WhistleblowerMessagesComponent {
  protected activeModal = inject(NgbActiveModal);

  @Input() tipService: ReceiverTipService;
}
