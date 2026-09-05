import {Component, ElementRef, OnInit, inject, viewChild} from "@angular/core";
import {FieldTemplatesResolver} from "@app/shared/resolvers/field-templates-resolver.service";
import {FieldUtilitiesService} from "@app/shared/services/field-utilities.service";
import {HttpService} from "@app/shared/services/http.service";
import {UtilsService} from "@app/shared/services/utils.service";
import {ParsedFields} from "@app/models/component-model/parsedFields";
import {fieldtemplatesResolverModel} from "@app/models/resolvers/field-template-model";
import {Step, questionnaireResolverModel} from "@app/models/resolvers/questionnaire-model"
import {AddFieldComponent} from "../add-field/add-field.component";;
import {FormsModule} from "@angular/forms";
import {FieldsComponent} from "../fields/fields.component";
import {TranslateModule} from "@ngx-translate/core";
import {PaginatedInterfaceComponent} from "@app/shared/components/paginated-interface/paginated-interface.component";


@Component({
    selector: "src-questions",
    templateUrl: "./questions.component.html",
    standalone: true,
    imports: [AddFieldComponent, FieldsComponent, FormsModule, PaginatedInterfaceComponent, TranslateModule]
})
export class QuestionsComponent implements OnInit {
  private readonly httpService = inject(HttpService);
  private readonly utilsService = inject(UtilsService);
  private readonly fieldTemplates = inject(FieldTemplatesResolver);
  private readonly fieldUtilities = inject(FieldUtilitiesService);

  showAddQuestion = false;
  fields: fieldtemplatesResolverModel[] = [];
  parsedFields: Record<string, ParsedFields> = {};
  questionnairesData: questionnaireResolverModel[] = [];
  step: Step;
  readonly uploadInput = viewChild<ElementRef<HTMLInputElement>>('uploadInput');

  ngOnInit(): void {
    this.getResolver();
  }

  toggleAddQuestion() {
    this.showAddQuestion = !this.showAddQuestion;
  };

  importQuestion(files: FileList | null): void {
    const file = files?.[0];
    if (file) {
      this.utilsService.readFileAsText(file).subscribe((txt) => {
        return this.httpService.requestImportAdminFieldTemplate(txt).subscribe({
          next:()=>{
            this.utilsService.reloadComponent();
          },
          error:()=>{
            const uploadInput = this.uploadInput();
            if (uploadInput) {
                uploadInput.nativeElement.value = "";
            }
          }
        });
      });
    }
  }

  getResolver() {
    return this.httpService.requestAdminFieldTemplateResource().subscribe(response => {
      this.fieldTemplates.dataModel = response;
      this.fields = response;
      this.fields = this.fields.filter((field: { editable: boolean; }) => field.editable);
      this.parseFields();
    });
  }

  parseFields() {
    this.parsedFields = {};
    this.fields.forEach(field => {
      this.parsedFields[field.id] = this.fieldUtilities.parseField(field, {
        fields: [],
        fields_by_id: {},
        options_by_id: {}
      });
    });
  }

  onAdd() {
    this.showAddQuestion = false;
    this.getResolver();
  }

  onDelete(id: string) {
    this.fields = this.fields.filter(i => i.id !== id);
    this.parseFields();
  }
}
