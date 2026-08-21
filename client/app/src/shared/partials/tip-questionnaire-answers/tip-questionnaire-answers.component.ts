import {CollapsiblePanelComponent} from "@app/shared/components/collapsible-panel/collapsible-panel.component";
import {Component, inject, input} from "@angular/core";
import {UtilsService} from "@app/shared/services/utils.service";
import {WbtipService} from "@app/services/helper/wbtip.service";
import {ReceiverTipService} from "@app/services/helper/receiver-tip.service";
import {NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {TipFieldComponent} from "../tip-field/tip-field.component";
import {TranslateModule} from "@ngx-translate/core";
import {OrderByPipe} from "@app/shared/pipes/order-by.pipe";

@Component({
    selector: "src-tip-questionnaire-answers",
    templateUrl: "./tip-questionnaire-answers.component.html",
    standalone: true,
    imports: [CollapsiblePanelComponent, NgbTooltipModule, TipFieldComponent, TranslateModule, OrderByPipe]
})
export class TipQuestionnaireAnswersComponent {
  protected utilsService = inject(UtilsService);

  readonly tipService = input.required<ReceiverTipService | WbtipService>();
  readonly redactOperationTitle = input<string>();
  readonly redactMode = input<boolean>();
  collapsed = false;

  public toggleCollapse() {
    this.collapsed = !this.collapsed;
  }
}
