import {Component, Input, inject} from "@angular/core";
import {UtilsService} from "@app/shared/services/utils.service";
import {WbtipService} from "@app/services/helper/wbtip.service";
import {ReceiverTipService} from "@app/services/helper/receiver-tip.service";
import {NgbTooltipModule, NgbModal} from "@ng-bootstrap/ng-bootstrap";
import {TipFieldComponent} from "../tip-field/tip-field.component";
import {TranslateModule} from "@ngx-translate/core";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {OrderByPipe} from "@app/shared/pipes/order-by.pipe";
import {FileInfoComponent} from "@app/shared/modals/file-info/file-info.component";

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
    // Get the first questionnaire (or you could iterate if there are multiple)
    const questionnaire = this.tipService.tip.questionnaires[0];

    if (!questionnaire || (!questionnaire.hash_sha256 && !questionnaire.hash_sha512)) {
      return;
    }

    // Open modal with questionnaire hash information
    const modalRef = this.modalService.open(FileInfoComponent);
    modalRef.componentInstance.file = {
      name: 'Questionnaire',
      type: 'application/json',
      size: JSON.stringify(questionnaire.answers).length,
      creation_date: new Date().toISOString(),
      hash_sha256: questionnaire.hash_sha256,
      hash_sha512: questionnaire.hash_sha512,
      description: ''
    };
    modalRef.componentInstance.receivers_by_id = this.tipService.tip.receivers_by_id;
  }
}
