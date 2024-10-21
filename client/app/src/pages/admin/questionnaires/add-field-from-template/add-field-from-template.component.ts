import { Component, EventEmitter, Input, OnInit, Output, inject } from "@angular/core";
import {HttpService} from "@app/shared/services/http.service";
import {UtilsService} from "@app/shared/services/utils.service";
import {NewField} from "@app/models/admin/new-field";
import {QuestionnaireService} from "@app/pages/admin/questionnaires/questionnaire.service";
import {Step} from "@app/models/resolvers/questionnaire-model";
import {Field, fieldtemplatesResolverModel} from "@app/models/resolvers/field-template-model";
import { FormsModule } from "@angular/forms";

import { TranslatorPipe } from "@app/shared/pipes/translate";
import { TranslateModule } from "@ngx-translate/core";

@Component({
    selector: "src-add-field-from-template",
    templateUrl: "./add-field-from-template.component.html",
    standalone: true,
    imports: [FormsModule, TranslatorPipe, TranslateModule]
})
export class AddFieldFromTemplateComponent implements OnInit {
  private questionnaireService = inject(QuestionnaireService);
  private httpService = inject(HttpService);
  private utilsService = inject(UtilsService);

  @Input() fieldTemplatesData: fieldtemplatesResolverModel[];
  @Input() step: Step;
  @Input() type: string;
  @Output() dataToParent = new EventEmitter<string>();

  fields: Step[] | Field[];
  new_field: { template_id: string } = {template_id: ""};

  ngOnInit(): void {
    if (this.step) {
      this.fields = this.step.children;
    }
  }

  addFieldFromTemplate(): void {
    if (this.type === "step") {
      const field = new NewField();
      field.step_id = this.step.id;
      field.template_id = "";

      field.template_id = this.new_field.template_id;
      field.instance = "reference";
      field.y = this.utilsService.newItemOrder(this.fields, "y");
      this.httpService.requestAddAdminQuestionnaireField(field).subscribe((newField: Field) => {
        this.fields.push(newField);
        this.new_field = {
          template_id: ""
        };
        this.dataToParent.emit();
        return this.questionnaireService.sendData();
      });
    }
    if (this.type === "field") {
      const field = new NewField();
      field.template_id = "";
      field.fieldgroup_id = this.step.id;

      field.template_id = this.new_field.template_id;
      field.instance = "reference";
      field.y = this.utilsService.newItemOrder(this.step.children, "y");
      field.template_id = this.new_field.template_id;
      if(field.template_id !== field.fieldgroup_id){
        this.httpService.requestAddAdminQuestionnaireField(field).subscribe((newField: Step) => {
          this.step.children.push(newField);
          this.new_field = {
            template_id: ""
          };
          this.dataToParent.emit();
          return this.questionnaireService.sendData();
        });
      }
    }
  }
}