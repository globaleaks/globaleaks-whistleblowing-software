import {ChangeDetectorRef, Component, Input, OnInit, inject} from "@angular/core";
import {ParsedFields} from "@app/models/component-model/parsedFields";
import {fieldtemplatesResolverModel} from "@app/models/resolvers/field-template-model";
import {Step, questionnaireResolverModel} from "@app/models/resolvers/questionnaire-model";
import {FieldTemplatesResolver} from "@app/shared/resolvers/field-templates-resolver.service";
import {HttpService} from "@app/shared/services/http.service";

import {AddFieldComponent} from "../add-field/add-field.component";
import {AddFieldFromTemplateComponent} from "../add-field-from-template/add-field-from-template.component";
import {FormsModule} from "@angular/forms";
import {FieldsComponent} from "../fields/fields.component";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {OrderByPipe} from "@app/shared/pipes/order-by.pipe";
import {TranslateModule} from "@ngx-translate/core";

@Component({
    selector: "src-step",
    templateUrl: "./step.component.html",
    standalone: true,
    imports: [AddFieldComponent, AddFieldFromTemplateComponent, FormsModule, FieldsComponent, TranslatorPipe, OrderByPipe, TranslateModule]
})
export class StepComponent implements OnInit {
  private cdr = inject(ChangeDetectorRef);
  private httpService = inject(HttpService);
  protected fieldTemplates = inject(FieldTemplatesResolver);

  @Input() step: Step;
  @Input() parsedFields: ParsedFields;
  showAddQuestion: boolean = false;
  showAddQuestionFromTemplate: boolean = false;
  fieldTemplatesData: fieldtemplatesResolverModel[] = [];

  ngOnInit(): void {
    if (Array.isArray(this.fieldTemplates.dataModel)) {
      this.fieldTemplatesData = this.fieldTemplates.dataModel;
    } else {
      this.fieldTemplatesData = [this.fieldTemplates.dataModel];
    }
  }

  toggleAddQuestion(): void {
    this.showAddQuestion = !this.showAddQuestion;
    this.showAddQuestionFromTemplate = false;
  }

  toggleAddQuestionFromTemplate(): void {
    this.showAddQuestionFromTemplate = !this.showAddQuestionFromTemplate;
    this.showAddQuestion = false;
  }

  listenToAddField() {
    this.showAddQuestion = false;
  }

  listenToAddFieldFormTemplate() {
    this.showAddQuestionFromTemplate = false;
  }

  listenToFields() {
    this.getResolver()
  }

  getResolver() {
    return this.httpService.requestQuestionnairesResource().subscribe(response => {
      response.forEach((step: questionnaireResolverModel) => {
        if (step.id === this.step.questionnaire_id) {
          step.steps.forEach((innerStep: any) => {
            if (innerStep.id === this.step.id) {
              this.step = innerStep;
            }
          })
          this.cdr.markForCheck();
        }
      });
    });
  }
}