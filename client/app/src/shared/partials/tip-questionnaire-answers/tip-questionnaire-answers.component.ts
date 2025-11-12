import {Component, Input, inject} from "@angular/core";
import {UtilsService} from "@app/shared/services/utils.service";
import {WbtipService} from "@app/services/helper/wbtip.service";
import {ReceiverTipService} from "@app/services/helper/receiver-tip.service";
import {NgbTooltipModule, NgbModal} from "@ng-bootstrap/ng-bootstrap";
import {TipFieldComponent} from "../tip-field/tip-field.component";
import {TranslateModule} from "@ngx-translate/core";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {OrderByPipe} from "@app/shared/pipes/order-by.pipe";
import {QuestionnaireAnswersInfoComponent} from "@app/shared/modals/questionnaire-answers-info/questionnaire-answers-info.component";

@Component({
    selector: "src-tip-questionnaire-answers",
    templateUrl: "./tip-questionnaire-answers.component.html",
    standalone: true,
    imports: [NgbTooltipModule, TipFieldComponent, TranslateModule, TranslatorPipe, OrderByPipe]
})
export class TipQuestionnaireAnswersComponent {
  protected utilsService = inject(UtilsService);
  private modalService = inject(NgbModal);

  @Input() tipService: ReceiverTipService | WbtipService;
  @Input() redactOperationTitle: string;
  @Input() redactMode: boolean;
  collapsed = false;

  public toggleCollapse() {
    this.collapsed = !this.collapsed;
  }

  public openAnswersInfo() {
    const answerHashes: any[] = [];

    // Iterate through all questionnaires
    for (const questionnaire of this.tipService.tip.questionnaires) {
      // Iterate through all steps in each questionnaire
      for (const step of questionnaire.steps) {
        if (!step.enabled) continue;

        // Iterate through all fields in each step
        for (const field of step.children) {
          if (!field.enabled) continue;

          // Get answers for this field
          const fieldAnswers = questionnaire.answers[field.id];
          if (fieldAnswers && Array.isArray(fieldAnswers)) {
            // Iterate through all entries for this field
            fieldAnswers.forEach((entry, entryIndex) => {
              if (entry && entry.value && (entry.hash_sha256 || entry.hash_sha512)) {
                answerHashes.push({
                  fieldLabel: field.label,
                  entryIndex: fieldAnswers.length > 1 ? entryIndex : null,
                  value: entry.value,
                  hash_sha256: entry.hash_sha256 || '',
                  hash_sha512: entry.hash_sha512 || ''
                });
              }
            });
          }
        }
      }
    }

    // Open modal with collected hashes
    const modalRef = this.modalService.open(QuestionnaireAnswersInfoComponent, { size: 'xl' });
    modalRef.componentInstance.answerHashes = answerHashes;
  }
}
