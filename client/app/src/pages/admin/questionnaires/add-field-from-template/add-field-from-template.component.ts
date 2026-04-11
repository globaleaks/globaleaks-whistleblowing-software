import {Component, EventEmitter, Input, OnInit, Output, inject} from "@angular/core";
import {HttpService} from "@app/shared/services/http.service";
import {UtilsService} from "@app/shared/services/utils.service";
import {NewField} from "@app/models/admin/new-field";
import {Step} from "@app/models/resolvers/questionnaire-model";
import {Field, fieldtemplatesResolverModel} from "@app/models/resolvers/field-template-model";
import {FormsModule} from "@angular/forms";

import {TranslatorPipe} from "@app/shared/pipes/translate";
import {TranslateModule} from "@ngx-translate/core";

@Component({
    selector: "src-add-field-from-template",
    templateUrl: "./add-field-from-template.component.html",
    standalone: true,
    imports: [FormsModule, TranslatorPipe, TranslateModule]
})
export class AddFieldFromTemplateComponent implements OnInit {
  private httpService = inject(HttpService);
  private utilsService = inject(UtilsService);

  @Input() fieldTemplatesData: fieldtemplatesResolverModel[];
  @Input() step: Step;
  @Input() type: string;
  @Output() added = new EventEmitter<void>();

  fields: Step[] | Field[];
  new_field: { template_id: string } = {template_id: ""};

  ngOnInit(): void {
    if (this.step) {
      this.fields = this.step.children;
    }
  }

  addFieldFromTemplate(): void {
    const templateId = this.new_field.template_id;
    if (!templateId) return;

    const isStep = this.type === "step";
    const isField = this.type === "field";
    if (!isStep && !isField) return;

    const parentId = this.step?.id;
    const list = isStep ? (this.fields as any[]) : (this.step.children as any[]);
    const ySource = isStep ? (this.fields as any[]) : (this.step.children as any[]);

    if (isField && templateId === parentId) return;

    const field = new NewField();
    field.template_id = templateId;
    field.instance = "reference";
    field.y = this.utilsService.newItemOrder(ySource, "y");

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
