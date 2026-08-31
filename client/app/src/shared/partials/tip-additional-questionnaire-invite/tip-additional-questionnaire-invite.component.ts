import {CollapsiblePanelComponent} from "@app/shared/components/collapsible-panel/collapsible-panel.component";
import {Component, inject, input, output} from "@angular/core";
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

  // Whoever is asked fills the questionnaire, whoever asked edits it; the sentence is the same for
  // both
  readonly askedByViewer = input(false);
  readonly edit = output<void>();

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
