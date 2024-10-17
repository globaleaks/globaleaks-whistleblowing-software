import { Component, Input } from '@angular/core';
import { Questionnaire } from '@app/models/reciever/reciever-tip-data';
import { UtilsService } from '@app/shared/services/utils.service';

@Component({
  selector: 'src-sendtip-detail-questionnaire-answers',
  templateUrl: './sendtip-detail-questionnaire-answers.component.html'
})
export class SendtipDetailQuestionnaireAnswersComponent{

  @Input() questionnaire: Questionnaire;

  @Input() label: string = 'Questionnaire answers';

  collapsed = false;

  constructor(protected utilsService: UtilsService) {
  }


  public toggleCollapse() {
    this.collapsed = !this.collapsed;
  }
}
