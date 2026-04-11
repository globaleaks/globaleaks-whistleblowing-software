import {Component, EventEmitter, Input, OnInit, Output, inject} from "@angular/core";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {HttpService} from "@app/shared/services/http.service";
import {UtilsService} from "@app/shared/services/utils.service";
import {NewStep} from "@app/models/admin/new-step";
import {Step, questionnaireResolverModel} from "@app/models/resolvers/questionnaire-model";
import {FormsModule} from "@angular/forms";
import {StepsListComponent} from "../steps-list/steps-list.component";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {TranslateModule} from "@ngx-translate/core";

@Component({
    selector: "src-steps",
    templateUrl: "./steps.component.html",
    standalone: true,
    imports: [FormsModule, StepsListComponent, TranslatorPipe, TranslateModule]
})
export class StepsComponent implements OnInit {
  protected node = inject(NodeResolver);
  protected utilsService = inject(UtilsService);
  private httpService = inject(HttpService);

  @Output() deleted = new EventEmitter<string>();
  @Input() questionnaire: questionnaireResolverModel;
  showAddStep = false;
  step: Step;
  editing = false;
  new_step: { label: string } = {label: ""};

  ngOnInit(): void {
    this.step = this.questionnaire.steps[0];
  }

  toggleAddStep() {
    this.showAddStep = !this.showAddStep;
  }

  addStep() {
    const step = new NewStep();
    step.questionnaire_id = this.questionnaire.id;
    step.label = this.new_step.label;
    step.order = this.utilsService.newItemOrder(this.questionnaire.steps, "order");

    this.httpService.requestAddAdminQuestionnaireStep(step).subscribe((newStep: Step) => {
      this.questionnaire.steps.push(newStep);
      this.new_step = {label: ""};
    });
  }

  onDelete(id: string) {
    this.questionnaire.steps = this.questionnaire.steps.filter(i => i.id !== id);
  }
}
