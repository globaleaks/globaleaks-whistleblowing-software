import {Component, Input, OnInit, inject} from "@angular/core";
import {DatePipe} from "@angular/common";
import {TranslateModule} from "@ngx-translate/core";
import {OrderByPipe} from "@app/shared/pipes/order-by.pipe";
import {CollapsiblePanelComponent} from "@app/shared/components/collapsible-panel/collapsible-panel.component";
import {TipFieldComponent} from "@app/shared/partials/tip-field/tip-field.component";
import {FieldUtilitiesService} from "@app/shared/services/field-utilities.service";
import {RecieverTipData} from "@app/models/receiver/receiver-tip-data";

@Component({
    selector: "src-tip-closure-questionnaire",
    templateUrl: "./tip-closure-questionnaire.component.html",
    standalone: true,
    imports: [CollapsiblePanelComponent, DatePipe, OrderByPipe, TipFieldComponent, TranslateModule]
})
export class TipClosureQuestionnaireComponent implements OnInit {
  private fieldUtilitiesService = inject(FieldUtilitiesService);

  @Input() tip: RecieverTipData;

  collapsed = false;

  ngOnInit(): void {
    const questionnaire = this.tip?.closure_questionnaire;
    if (questionnaire) {
      // The archived steps carry no enabled flag: evaluate the trigger logic
      // against the answers, as done for the questionnaires of the report
      this.fieldUtilitiesService.parseQuestionnaire(questionnaire as any, {fields: [], fields_by_id: {}, options_by_id: {}});
      this.fieldUtilitiesService.onAnswersUpdate({questionnaire: questionnaire, answers: questionnaire.answers, uploads: {}});
    }
  }
}
