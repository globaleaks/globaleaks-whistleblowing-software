import {Component, EventEmitter, Input, OnInit, Output, inject} from "@angular/core";
import {HttpService} from "@app/shared/services/http.service";
import {UtilsService} from "@app/shared/services/utils.service";
import {NewField} from "@app/models/admin/new-field";
import {FieldTemplate} from "@app/models/admin/field-Template";
import {QuestionnaireService} from "@app/pages/admin/questionnaires/questionnaire.service";
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
export class AddFieldComponent implements OnInit {
  private questionnaireService = inject(QuestionnaireService);
  private httpService = inject(HttpService);
  private utilsService = inject(UtilsService);

  @Output() dataToParent = new EventEmitter<string>();
  @Input() step: Step;
  @Input() type: string;
  new_field: { label: string, type: string } = {label: "", type: ""};
  fields: Step[] | Field[];

  ngOnInit(): void {
    if (this.step) {
      this.fields = this.step.children;
    }
  }

  addField() {
    if (this.type === "step") {

      const field = new NewField();
      field.step_id = this.step.id;
      field.template_id = "";
      field.label = this.new_field.label;
      field.type = this.new_field.type;
      field.y = this.utilsService.newItemOrder(this.fields, "y");

      if (field.type === "fileupload") {
        field.multi_entry = true;
      }
      this.httpService.requestAddAdminQuestionnaireField(field).subscribe((newField: Field) => {
        this.fields.push(newField);
        this.new_field = {
          label: "",
          type: ""
        };
        this.dataToParent.emit();
      });
    }
    if (this.type === "template") {
      const field = new FieldTemplate();
      field.fieldgroup_id = this.fields ? this.fields[0].id : "";
      field.instance = "template";
      field.label = this.new_field.label;
      field.type = this.new_field.type;
      this.httpService.requestAddAdminQuestionnaireFieldTemplate(field).subscribe(() => {
        this.new_field = {
          label: "",
          type: ""
        };
        this.dataToParent.emit();
        return this.questionnaireService.sendData();
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
        this.dataToParent.emit();
      });
    }
  }
}