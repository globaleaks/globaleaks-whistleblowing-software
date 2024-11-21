import {Injectable} from '@angular/core';
import {FieldUtilitiesService} from "@app/shared/services/field-utilities.service";
import { UtilsService } from './utils.service';
import { Subject } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class TipService {

  private reloadSubject = new Subject<void>();
  reload$ = this.reloadSubject.asObservable();

  constructor(private fieldUtilities: FieldUtilitiesService, private utilsService: UtilsService) {
  }

  triggerReload(): void {
    this.reloadSubject.next();
  }

  filterNotTriggeredField(tip: any, parent: any, field: any, answers: any): void {
    let i;
    if (this.fieldUtilities.isFieldTriggered(parent, field, answers, tip.score)) {
      for (i = 0; i < field.children.length; i++) {
        this.filterNotTriggeredField(tip, field, field.children[i], answers);
      }
    }
  }

  preprocessTipAnswers(tip: any) {
    let x, i, j, k, step;

    for (x = 0; x < tip.questionnaires.length; x++) {
      let questionnaire = tip.questionnaires[x];
      this.fieldUtilities.parseQuestionnaire(questionnaire, {fields: [], fields_by_id: {}, options_by_id: {}});

      for (i = 0; i < questionnaire.steps.length; i++) {
        step = questionnaire.steps[i];
        if (this.fieldUtilities.isFieldTriggered(null, step, questionnaire.answers, tip.score)) {
          for (j = 0; j < step.children.length; j++) {
            this.filterNotTriggeredField(tip, step, step.children[j], questionnaire.answers);
          }
        }
      }

      for (i = 0; i < questionnaire.steps.length; i++) {
        step = questionnaire.steps[i];
        j = step.children.length;
        while (j--) {
          if (step.children[j]["template_id"] === "whistleblower_identity") {
            tip.whistleblower_identity_field = step.children[j];
            tip.whistleblower_identity_field.enabled = true;
            step.children.splice(j, 1);

            questionnaire = {
              steps: [{...tip.whistleblower_identity_field}]
            };

            tip.fields = questionnaire.steps[0].children;
            this.fieldUtilities.onAnswersUpdate(this);

            for (k = 0; k < tip.whistleblower_identity_field.children.length; k++) {
              this.filterNotTriggeredField(tip, tip.whistleblower_identity_field, tip.whistleblower_identity_field.children[k], tip.data.whistleblower_identity);
            }
          }
        }
      }
    }
  }


  preprocessForwardingAnswers(forwarding: any){

    let i, step, j;

    let questionnaire = forwarding.questionnaire;
    this.fieldUtilities.parseQuestionnaire(questionnaire, {fields: [], fields_by_id: {}, options_by_id: {}});

    for (i = 0; i < questionnaire.steps.length; i++) {
      step = questionnaire.steps[i];
      if (this.fieldUtilities.isFieldTriggered(null, step, questionnaire.answers, 0)) {
        for (j = 0; j < step.children.length; j++) {
          this.filterNotTriggeredField({score: 0}, step, step.children[j], questionnaire.answers);
        }
      }
    }

  }


}
