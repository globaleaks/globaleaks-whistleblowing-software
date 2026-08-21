import {CollapsiblePanelComponent} from "@app/shared/components/collapsible-panel/collapsible-panel.component";
import {Component, inject} from "@angular/core";
import {UtilsService} from "@app/shared/services/utils.service";
import {NgbModal} from "@ng-bootstrap/ng-bootstrap";
import {
  TipAdditionalQuestionnaireFormComponent
} from "@app/shared/modals/tip-additional-questionnaire-form/tip-additional-questionnaire-form.component";

import {TranslateModule} from "@ngx-translate/core";

@Component({
    selector: "src-tip-additional-questionnaire-invite",
    templateUrl: "./tip-additional-questionnaire-invite.component.html",
    standalone: true,
    imports: [CollapsiblePanelComponent, TranslateModule]
})
export class TipAdditionalQuestionnaireInviteComponent {
  protected utilsService = inject(UtilsService);
  private modalService = inject(NgbModal);

  collapsed = false;

  public toggleColLapse() {
    this.collapsed = !this.collapsed;
  }

  tipOpenAdditionalQuestionnaire() {
    this.modalService.open(TipAdditionalQuestionnaireFormComponent, {
      windowClass: "custom-modal-width",
      backdrop: 'static',
      keyboard: false
    });
  }
}
