import {Component, Input, inject} from "@angular/core";
import {NgForm, FormsModule} from "@angular/forms";
import {DeleteConfirmationComponent} from "@app/shared/modals/delete-confirmation/delete-confirmation.component";
import {NgbModal} from "@ng-bootstrap/ng-bootstrap";
import {
  QuestionnaireDuplicationComponent
} from "@app/shared/modals/questionnaire-duplication/questionnaire-duplication.component";
import {HttpService} from "@app/shared/services/http.service";
import {UtilsService} from "@app/shared/services/utils.service";
import {QuestionnaireService} from "@app/pages/admin/questionnaires/questionnaire.service";
import {Observable} from "rxjs";
import {questionnaireResolverModel} from "@app/models/resolvers/questionnaire-model";
import {AuthenticationService} from "@app/services/helper/authentication.service";

import {StepsComponent} from "../steps/steps.component";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {TranslateModule} from "@ngx-translate/core";

@Component({
    selector: "src-questionnaires-list",
    templateUrl: "./questionnaires-list.component.html",
    standalone: true,
    imports: [FormsModule, StepsComponent, TranslatorPipe, TranslateModule]
})
export class QuestionnairesListComponent {
  private authenticationService = inject(AuthenticationService);
  private questionnaireService = inject(QuestionnaireService);
  private modalService = inject(NgbModal);
  private httpService = inject(HttpService);
  private utilsService = inject(UtilsService);

  @Input() questionnaire: questionnaireResolverModel;
  @Input() questionnaires: questionnaireResolverModel[];
  @Input() editQuestionnaire: NgForm;
  editing: boolean = false;

  toggleEditing(questionnaire: questionnaireResolverModel) {
    this.editing = questionnaire.editable && !this.editing;
  }

  saveQuestionnaire(questionnaire: questionnaireResolverModel) {
    this.httpService.requestUpdateAdminQuestionnaire(questionnaire.id, questionnaire).subscribe(_ => {
      this.editing = false;
      return this.questionnaireService.sendData();
    });
  }

  exportQuestionnaire(questionnaire: questionnaireResolverModel) {
    this.utilsService.saveAs(this.authenticationService, questionnaire.name + ".json", "api/admin/questionnaires/" + questionnaire.id + "?multilang=1");
  }

  duplicateQuestionnaire(questionnaire: questionnaireResolverModel) {
    const modalRef = this.modalService.open(QuestionnaireDuplicationComponent, {backdrop: 'static', keyboard: false});
    modalRef.componentInstance.questionnaire = questionnaire;
    modalRef.componentInstance.operation = "duplicate";
    return modalRef.result;
  }

  deleteQuestionnaire(questionnaire: questionnaireResolverModel) {
    this.openConfirmableModalDialog(questionnaire, "").subscribe();
  }

  openConfirmableModalDialog(arg: questionnaireResolverModel, scope: any): Observable<string> {
    scope = !scope ? this : scope;
    return new Observable((observer) => {
      const modalRef = this.modalService.open(DeleteConfirmationComponent, {backdrop: 'static', keyboard: false});
      modalRef.componentInstance.arg = arg;
      modalRef.componentInstance.scope = scope;

      modalRef.componentInstance.confirmFunction = () => {
        observer.complete()
        return this.httpService.requestDeleteAdminQuestionnaire(arg.id).subscribe(_ => {
          this.utilsService.deleteResource(this.questionnaires, arg);
        });
      };
    });
  }
}
