import {Component, OnInit, inject, input, output} from "@angular/core";
import {HttpService} from "@app/shared/services/http.service";
import {UtilsService} from "@app/shared/services/utils.service";
import {NewField} from "@app/models/admin/new-field";
import {Step} from "@app/models/resolvers/questionnaire-model";
import {Field, fieldtemplatesResolverModel} from "@app/models/resolvers/field-template-model";
import {FormsModule} from "@angular/forms";

import {TranslateModule} from "@ngx-translate/core";

@Component({
    selector: "src-add-field-from-template",
    templateUrl: "./add-field-from-template.component.html",
    standalone: true,
    imports: [FormsModule, TranslateModule]
})
export class AddFieldFromTemplateComponent implements OnInit {
  private httpService = inject(HttpService);
  private utilsService = inject(UtilsService);

  readonly fieldTemplatesData = input<fieldtemplatesResolverModel[]>();
  readonly step = input.required<Step>();
  readonly type = input<string>();
  readonly added = output<void>();

  fields: Step[] | Field[];
  new_field: { template_id: string } = {template_id: ""};

  ngOnInit(): void {
    const step = this.step();
    if (step) {
      this.fields = step.children;
    }
  }

  addFieldFromTemplate(): void {
    const templateId = this.new_field.template_id;
    if (!templateId) return;

    const isStep = this.type() === "step";
    const isField = this.type() === "field";
    if (!isStep && !isField) return;

    const step = this.step();
    const parentId = step?.id;
    const list = isStep ? (this.fields as any[]) : (step.children as any[]);
    const ySource = isStep ? (this.fields as any[]) : (step.children as any[]);

    if (isField && templateId === parentId) return;

    const field = new NewField();
    field.template_id = templateId;
    field.instance = "reference";
    field.y = this.utilsService.newItemOrder(ySource, "y");

    // The question references its template: it has to carry its type too, or
    // the editor presents it as a question of the default type until the
    // questionnaire is reloaded
    const template = this.fieldTemplatesData()?.find(fieldTemplate => fieldTemplate.id === templateId);
    if (template) {
      field.type = template.type;
      field.statistical = template.statistical;
    }

    if (isStep) {
      field.step_id = parentId;
    } else {
      field.fieldgroup_id = parentId;
    }

    this.httpService.requestAddAdminQuestionnaireField(field).subscribe((created: any) => {
      list.push(created);
      this.new_field.template_id = "";
      this.added.emit();
    });
  }
}
