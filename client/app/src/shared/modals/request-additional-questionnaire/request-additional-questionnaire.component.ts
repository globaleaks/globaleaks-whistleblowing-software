import {Component, OnInit, inject} from "@angular/core";
import {NgbActiveModal} from "@ng-bootstrap/ng-bootstrap";
import {NgSelectComponent, NgLabelTemplateDirective} from "@ng-select/ng-select";
import {FormsModule} from "@angular/forms";
import {TranslateModule} from "@ngx-translate/core";
import {RequestableQuestionnaire} from "@app/models/receiver/receiver-tip-data";

/**
 * The additional questionnaire the recipients ask of the report they are
 * reading is chosen among the ones its channel names, and the one already
 * asked of it is presented as chosen: leaving nothing chosen withdraws it,
 * choosing another one replaces it. The modal returns the decision and asks
 * nothing itself.
 */
@Component({
    selector: "src-request-additional-questionnaire",
    templateUrl: "./request-additional-questionnaire.component.html",
    standalone: true,
    imports: [NgSelectComponent, FormsModule, NgLabelTemplateDirective, TranslateModule]
})
export class RequestAdditionalQuestionnaireComponent implements OnInit {
  private readonly activeModal = inject(NgbActiveModal);

  selectableQuestionnaires: RequestableQuestionnaire[];
  // The questionnaire the report is already asked, if any
  requestedId = "";
  questionnaire: RequestableQuestionnaire | null = null;

  ngOnInit(): void {
    this.questionnaire = this.selectableQuestionnaires
                             .find(questionnaire => questionnaire.id === this.requestedId) || null;
  }

  // Confirming has an effect only where it changes what the report is asked:
  // withdrawing a request that stands, or asking a different questionnaire
  hasDecision(): boolean {
    return (this.questionnaire ? this.questionnaire.id : "") !== this.requestedId;
  }

  confirm() {
    this.activeModal.close({questionnaire: this.questionnaire ? this.questionnaire.id : ""});
  }

  cancel() {
    return this.activeModal.dismiss();
  }
}
