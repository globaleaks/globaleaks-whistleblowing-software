import {HttpClient} from "@angular/common/http";
import {Component, ElementRef, OnInit, ViewChild, inject} from "@angular/core";
import {questionnaireResolverModel} from "@app/models/resolvers/questionnaire-model";
import {QuestionnairesResolver} from "@app/shared/resolvers/questionnaires.resolver";
import {HttpService} from "@app/shared/services/http.service";
import {UtilsService} from "@app/shared/services/utils.service";
import {NewQuestionare} from "@app/models/admin/new-questionare";
import {NgClass} from "@angular/common";
import {FormsModule} from "@angular/forms";
import {QuestionnairesListComponent} from "../questionnaires-list/questionnaires-list.component";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {TranslateModule} from "@ngx-translate/core";
import {NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {PaginatedInterfaceComponent} from "@app/shared/components/paginated-interface/paginated-interface.component";


@Component({
    selector: "src-main",
    templateUrl: "./main.component.html",
    standalone: true,
    imports: [FormsModule, NgbTooltipModule, NgClass, PaginatedInterfaceComponent, QuestionnairesListComponent, TranslatorPipe, TranslateModule]
})
export class MainComponent implements OnInit {
  private http = inject(HttpClient);
  private httpService = inject(HttpService);
  private utilsService = inject(UtilsService);
  protected questionnairesResolver = inject(QuestionnairesResolver);

  questionnairesData: questionnaireResolverModel[] = [];
  new_questionnaire: { name: string } = {name: ""};
  showAddQuestionnaire = false;
  @ViewChild('keyUploadInput') keyUploadInput: ElementRef<HTMLInputElement>;

  ngOnInit(): void {
    this.questionnairesData = this.questionnairesResolver.dataModel;
  }

  addQuestionnaire() {
    const questionnaire: NewQuestionare = new NewQuestionare();
    questionnaire.name = this.new_questionnaire.name;
    this.httpService.addQuestionnaire(questionnaire).subscribe(res => {
      this.questionnairesData.push(res);
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
        return this.http.post("api/admin/questionnaires?multilang=1", txt).subscribe({
          next:()=>{
            this.getResolver();
          },
          error:()=>{
            if (this.keyUploadInput) {
                this.keyUploadInput.nativeElement.value = "";
            }
          }
        });
      });
    }
  }

  getResolver() {
    return this.httpService.requestQuestionnairesResource().subscribe((response: questionnaireResolverModel[]) => {
      this.questionnairesResolver.dataModel = response;
      this.questionnairesData = response;
    });
  }

  trackByFn(_: number, item: questionnaireResolverModel) {
    return item.id;
  }

  onDelete(id: string) {
    this.questionnairesData = this.questionnairesData.filter(i => i.id !== id);
  }
}
