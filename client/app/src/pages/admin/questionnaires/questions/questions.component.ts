import {HttpClient} from "@angular/common/http";
import {Component, ElementRef, OnDestroy, OnInit, ViewChild, inject} from "@angular/core";
import {FieldTemplatesResolver} from "@app/shared/resolvers/field-templates-resolver.service";
import {QuestionnairesResolver} from "@app/shared/resolvers/questionnaires.resolver";
import {HttpService} from "@app/shared/services/http.service";
import {UtilsService} from "@app/shared/services/utils.service";
import {QuestionnaireService} from "@app/pages/admin/questionnaires/questionnaire.service";
import {Subject, takeUntil} from "rxjs";
import {fieldtemplatesResolverModel} from "@app/models/resolvers/field-template-model";
import {Step, questionnaireResolverModel} from "@app/models/resolvers/questionnaire-model";

import {AddFieldComponent} from "../add-field/add-field.component";
import {FormsModule} from "@angular/forms";
import {FieldsComponent} from "../fields/fields.component";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {OrderByPipe} from "@app/shared/pipes/order-by.pipe";
import {TranslateModule} from "@ngx-translate/core";

@Component({
    selector: "src-questions",
    templateUrl: "./questions.component.html",
    standalone: true,
    imports: [AddFieldComponent, FormsModule, FieldsComponent, TranslatorPipe, OrderByPipe, TranslateModule]
})
export class QuestionsComponent implements OnInit, OnDestroy {
  private questionnaireService = inject(QuestionnaireService);
  private httpClient = inject(HttpClient);
  private httpService = inject(HttpService);
  private utilsService = inject(UtilsService);
  private fieldTemplates = inject(FieldTemplatesResolver);
  private questionnairesResolver = inject(QuestionnairesResolver);

  showAddQuestion: boolean = false;
  fields: fieldtemplatesResolverModel[];
  questionnairesData: questionnaireResolverModel[] = [];
  step: Step;
  @ViewChild('uploadInput') uploadInput: ElementRef<HTMLInputElement>;

  private destroy$ = new Subject<void>();

  ngOnInit(): void {
    this.questionnaireService.sharedData = "template";
    this.questionnaireService.getQuestionnairesData().pipe(takeUntil(this.destroy$)).subscribe(() => {
      this.getResolver();
      return this.getQuestionnairesResolver();
    });
    this.questionnairesData = this.questionnairesResolver.dataModel;
    if (Array.isArray(this.fieldTemplates.dataModel)) {
      this.fields = this.fieldTemplates.dataModel;
    } else {
      this.fields = [this.fieldTemplates.dataModel];
    }
    this.fields = this.fields.filter((field: { editable: boolean; }) => field.editable);
  }

  toggleAddQuestion() {
    this.showAddQuestion = !this.showAddQuestion;
  };

  importQuestion(files: FileList | null): void {
    if (files && files.length > 0) {
      this.utilsService.readFileAsText(files[0]).subscribe((txt) => {
        return this.httpClient.post("api/admin/fieldtemplates?multilang=1", txt).subscribe({
          next:()=>{
            this.utilsService.reloadComponent();
          },
          error:()=>{
            if (this.uploadInput) {
                this.uploadInput.nativeElement.value = "";
            }
          }
        });
      });
    }
  }

  getQuestionnairesResolver() {
    return this.httpService.requestQuestionnairesResource().subscribe((response: questionnaireResolverModel[]) => {
      this.questionnairesResolver.dataModel = response;
      this.questionnairesData = response;
    });
  }

  getResolver() {
    return this.httpService.requestAdminFieldTemplateResource().subscribe(response => {
      this.fieldTemplates.dataModel = response;
      this.fields = response;
      this.fields = this.fields.filter((field: { editable: boolean; }) => field.editable);
    });
  }

  listenToAddField() {
    this.showAddQuestion = false;
  }

  ngOnDestroy() {
    this.destroy$.next();
    this.destroy$.complete();
  }
}