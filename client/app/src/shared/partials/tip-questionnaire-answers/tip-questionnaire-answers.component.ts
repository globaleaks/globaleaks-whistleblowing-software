import { Component, Input, inject } from "@angular/core";
import {UtilsService} from "@app/shared/services/utils.service";
import {WbtipService} from "@app/services/helper/wbtip.service";
import {ReceiverTipService} from "@app/services/helper/receiver-tip.service";

import { TipFieldComponent } from "../tip-field/tip-field.component";
import { TranslateModule } from "@ngx-translate/core";
import { TranslatorPipe } from "@app/shared/pipes/translate";
import { OrderByPipe } from "@app/shared/pipes/order-by.pipe";

@Component({
    selector: "src-tip-questionnaire-answers",
    templateUrl: "./tip-questionnaire-answers.component.html",
    standalone: true,
    imports: [TipFieldComponent, TranslateModule, TranslatorPipe, OrderByPipe]
})
export class TipQuestionnaireAnswersComponent {
  protected utilsService = inject(UtilsService);

  @Input() tipService: ReceiverTipService | WbtipService;
  @Input() redactOperationTitle: string;
  @Input() redactMode: boolean;
  collapsed = false;

  public toggleCollapse() {
    this.collapsed = !this.collapsed;
  }
}
