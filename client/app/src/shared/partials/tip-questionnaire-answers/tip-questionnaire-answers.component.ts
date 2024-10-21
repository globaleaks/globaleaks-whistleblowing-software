import {Component, Input} from "@angular/core";
import {UtilsService} from "@app/shared/services/utils.service";
import {WbtipService} from "@app/services/helper/wbtip.service";
import {ReceiverTipService} from "@app/services/helper/receiver-tip.service";

@Component({
  selector: "src-tip-questionnaire-answers",
  templateUrl: "./tip-questionnaire-answers.component.html"
})
export class TipQuestionnaireAnswersComponent {
  @Input() tipService: ReceiverTipService | WbtipService;
  @Input() redactOperationTitle: string;
  @Input() redactMode: boolean;
  @Input() label: string = 'Questionnaire answers';

  @Input() isForwarding: boolean = false;

  collapsed = false;

  constructor(protected utilsService: UtilsService) {
  }

  public toggleCollapse() {
    this.collapsed = !this.collapsed;
  }
}
