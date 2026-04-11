import {Component, EventEmitter, Input, Output, inject} from "@angular/core";
import {HttpService} from "@app/shared/services/http.service";
import {UtilsService} from "@app/shared/services/utils.service";
import {NewField} from "@app/models/admin/new-field";
import {FieldTemplate} from "@app/models/admin/field-Template";
import {fieldtemplatesResolverModel} from "@app/models/resolvers/field-template-model";
import {Step} from "@app/models/resolvers/questionnaire-model";
import {Field} from "@app/models/resolvers/field-template-model";
import {FormsModule} from "@angular/forms";

import {TranslatorPipe} from "@app/shared/pipes/translate";
import {TranslateModule} from "@ngx-translate/core";

@Component({
    selector: "src-add-field",
    templateUrl: "./add-field.component.html",
    standalone: true,
    imports: [FormsModule, TranslatorPipe, TranslateModule]
})
export class AddFieldComponent {
  private httpService = inject(HttpService);
  private utilsService = inject(UtilsService);

  @Input() step: Step;
  @Input() fields: fieldtemplatesResolverModel[];
  @Input() type: string;
  @Output() added = new EventEmitter<void>();
  new_field: { label: string, type: string } = {label: "", type: ""};

  addField() {
    if (this.type === "step") {
      const field = new NewField();
      field.step_id = this.step.id;
      field.template_id = "";
      field.label = this.new_field.label;
      field.type = this.new_field.type;
      field.y = this.utilsService.newItemOrder(this.step.children, "y");

      if (field.type === "fileupload") {
        field.multi_entry = true;
      }
      this.httpService.requestAddAdminQuestionnaireField(field).subscribe((newField: Field) => {
        this.step.children.push(newField);
        this.new_field = {
          label: "",
          type: ""
        };
        this.added.emit();
      });
    }
    if (this.type === "template") {
      const field = new FieldTemplate();
      field.fieldgroup_id = "";
      field.instance = "template";
      field.label = this.new_field.label;
      field.type = this.new_field.type;
      this.httpService.requestAddAdminQuestionnaireFieldTemplate(field).subscribe((newField: FieldTemplate) => {
	this.fields.push(newField as unknown as Field);
        this.new_field = {
          label: "",
          type: ""
        };
        this.added.emit();
      });
    }
    if (this.type === "field") {
      const field = new NewField();
      field.fieldgroup_id = this.step.id;
      field.template_id = "";

      field.label = this.new_field.label;
      field.type = this.new_field.type;
      field.y = this.utilsService.newItemOrder(this.step.children, "y");

      if (field.type === "fileupload") {
        field.multi_entry = true;
      }
      field.instance = this.step.instance;
      this.httpService.requestAddAdminQuestionnaireField(field).subscribe((newField: Step) => {
        this.step.children.push(newField);
        this.new_field = {
          label: "",
          type: ""
        };
	this.added.emit();
      });
    }
  }
}
