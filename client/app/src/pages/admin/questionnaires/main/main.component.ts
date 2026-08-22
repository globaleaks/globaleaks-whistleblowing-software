import {Component, ElementRef, computed, inject, viewChild} from "@angular/core";
import {questionnaireResolverModel} from "@app/models/resolvers/questionnaire-model";
import {QuestionnairesResolver} from "@app/shared/resolvers/questionnaires.resolver";
import {HttpService} from "@app/shared/services/http.service";
import {UtilsService} from "@app/shared/services/utils.service";
import {NewQuestionare} from "@app/models/admin/new-questionare";
import {FormsModule} from "@angular/forms";
import {QuestionnairesListComponent} from "../questionnaires-list/questionnaires-list.component";
import {TranslateModule} from "@ngx-translate/core";
import {NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {PaginatedInterfaceComponent} from "@app/shared/components/paginated-interface/paginated-interface.component";


@Component({
    selector: "src-main",
    templateUrl: "./main.component.html",
    standalone: true,
    imports: [FormsModule, NgbTooltipModule, PaginatedInterfaceComponent, QuestionnairesListComponent, TranslateModule]
})
export class MainComponent {
  private httpService = inject(HttpService);
  private utilsService = inject(UtilsService);
  protected questionnairesResolver = inject(QuestionnairesResolver);

  readonly questionnairesData = computed(() => this.questionnairesResolver.resource.value());
  new_questionnaire: { name: string } = {name: ""};
  showAddQuestionnaire = false;
  readonly keyUploadInput = viewChild<ElementRef<HTMLInputElement>>('keyUploadInput');

  addQuestionnaire() {
    const questionnaire: NewQuestionare = new NewQuestionare();
    questionnaire.name = this.new_questionnaire.name;
    this.httpService.addQuestionnaire(questionnaire).subscribe(() => {
      this.new_questionnaire = {name: ""};
      this.getResolver();
    });
  }

  toggleAddQuestionnaire(): void {
    this.showAddQuestionnaire = !this.showAddQuestionnaire;
  }

  importQuestionnaire(files: FileList | null) {
    if (files && files.length > 0) {
      this.utilsService.readFileAsText(files[0]).subscribe((txt) => {
        return this.httpService.requestImportAdminQuestionnaire(txt).subscribe({
          next:()=>{
            this.getResolver();
          },
          error:()=>{
            const keyUploadInput = this.keyUploadInput();
            if (keyUploadInput) {
                keyUploadInput.nativeElement.value = "";
            }
          }
        });
      });
    }
  }

  getResolver(): void {
    this.questionnairesResolver.reload();
  }

  trackByFn(_: number, item: questionnaireResolverModel) {
    return item.id;
  }

  onDelete(id: string) {
    this.questionnairesResolver.resource.update(questionnaires => questionnaires.filter(i => i.id !== id));
  }
}
