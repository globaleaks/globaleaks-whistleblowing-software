import {Component, OnInit, inject, input, output} from "@angular/core";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {FieldUtilitiesService} from "@app/shared/services/field-utilities.service";
import {ParsedFields} from "@app/models/component-model/parsedFields";
import {HttpService} from "@app/shared/services/http.service";
import {UtilsService} from "@app/shared/services/utils.service";
import {NewStep} from "@app/models/admin/new-step";
import {Step, questionnaireResolverModel} from "@app/models/resolvers/questionnaire-model";
import {FormsModule} from "@angular/forms";
import {StepsListComponent} from "../steps-list/steps-list.component";
import {TranslatePipe} from "@ngx-translate/core";

@Component({
    selector: "src-steps",
    templateUrl: "./steps.component.html",
    standalone: true,
    imports: [FormsModule, StepsListComponent, TranslatePipe]
})
export class StepsComponent implements OnInit {
  protected node = inject(NodeResolver);
  protected utilsService = inject(UtilsService);
  private httpService = inject(HttpService);
  private fieldUtilities = inject(FieldUtilitiesService);

  readonly deleted = output<string>();
  readonly questionnaire = input.required<questionnaireResolverModel>();
  showAddStep = false;
  step: Step;
  editing = false;
  new_step: { label: string } = {label: ""};
  parsedFields: ParsedFields;

  ngOnInit(): void {
    this.step = this.questionnaire().steps[0];
    this.recompute();
  }

  // The questions that can trigger are gathered from every step, so that a question added, changed or
  // deleted in one step is offered, or no longer, as a trigger in all the others. The triggers on an
  // option that is gone are dropped, as the backend drops them along with the option.
  recompute(): void {
    const parsedFields = this.fieldUtilities.parseQuestionnaire(this.questionnaire(), {
      fields: [],
      fields_by_id: {},
      options_by_id: {}
    });

    const prune = (item: { triggered_by_options?: { option: string }[], children?: any[] }) => {
      if (item.triggered_by_options) {
        item.triggered_by_options = item.triggered_by_options.filter(trigger => trigger.option in parsedFields.options_by_id);
      }
      item.children?.forEach(prune);
    };
    this.questionnaire().steps.forEach(prune);

    this.parsedFields = parsedFields;
  }

  toggleAddStep() {
    this.showAddStep = !this.showAddStep;
  }

  addStep() {
    const step = new NewStep();
    step.questionnaire_id = this.questionnaire().id;
    step.label = this.new_step.label;
    step.order = this.utilsService.newItemOrder(this.questionnaire().steps, "order");

    this.httpService.requestAddAdminQuestionnaireStep(step).subscribe((newStep: Step) => {
      this.questionnaire().steps.push(newStep);
      this.new_step = {label: ""};
      this.recompute();
    });
  }

  onDelete(id: string) {
    this.questionnaire().steps = this.questionnaire().steps.filter(i => i.id !== id);
    this.recompute();
  }
}
