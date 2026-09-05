import {Component, inject, input, output} from "@angular/core";
import {NgForm, FormsModule} from "@angular/forms";
import {DeleteConfirmationComponent} from "@app/shared/modals/delete-confirmation/delete-confirmation.component";
import {NgbModal} from "@ng-bootstrap/ng-bootstrap";
import {
  QuestionnaireDuplicationComponent
} from "@app/shared/modals/questionnaire-duplication/questionnaire-duplication.component";
import {HttpService} from "@app/shared/services/http.service";
import {UtilsService} from "@app/shared/services/utils.service";
import {Observable} from "rxjs";
import {questionnaireResolverModel} from "@app/models/resolvers/questionnaire-model";
import {AuthenticationService} from "@app/services/helper/authentication.service";

import {StepsComponent} from "../steps/steps.component";
import {ListItemComponent} from "@app/shared/components/list-item/list-item.component";
import {TranslateModule} from "@ngx-translate/core";

@Component({
    selector: "src-questionnaires-list",
    templateUrl: "./questionnaires-list.component.html",
    standalone: true,
    imports: [FormsModule, StepsComponent, TranslateModule, ListItemComponent]
})
export class QuestionnairesListComponent {
  private readonly authenticationService = inject(AuthenticationService);
  private readonly modalService = inject(NgbModal);
  private readonly httpService = inject(HttpService);
  private readonly utilsService = inject(UtilsService);

  readonly questionnaire = input.required<questionnaireResolverModel>();
  readonly questionnaires = input<questionnaireResolverModel[]>();
  readonly editQuestionnaire = input.required<NgForm>();
  readonly deleted = output<string>();
  readonly duplicated = output<void>();
  editing = false;

  saveQuestionnaire(questionnaire: questionnaireResolverModel) {
    this.httpService.requestUpdateAdminQuestionnaire(questionnaire.id, questionnaire).subscribe();
  }

  exportQuestionnaire(questionnaire: questionnaireResolverModel) {
    this.utilsService.saveAs(this.authenticationService, questionnaire.name + ".json", "api/admin/questionnaires/" + questionnaire.id + "?multilang=1");
  }

  duplicateQuestionnaire(questionnaire: questionnaireResolverModel) {
    const modalRef = this.modalService.open(QuestionnaireDuplicationComponent, {backdrop: 'static', keyboard: false});
    modalRef.componentInstance.questionnaire = questionnaire;
    modalRef.componentInstance.operation = "duplicate";
    modalRef.componentInstance.confirmFunction = () => {
        this.duplicated.emit();
    }
    return modalRef.result;
  }

  deleteQuestionnaire(questionnaire: questionnaireResolverModel) {
    this.openConfirmableModalDialog(questionnaire, "").subscribe();
  }

  openConfirmableModalDialog(arg: questionnaireResolverModel, scope: any): Observable<string> {
    scope = !scope ? this : scope;
    return new Observable(() => {
      const modalRef = this.modalService.open(DeleteConfirmationComponent, {backdrop: 'static', keyboard: false});
      modalRef.componentInstance.arg = arg;
      modalRef.componentInstance.scope = scope;

      modalRef.componentInstance.confirmFunction = () => {
        return this.httpService.requestDeleteAdminQuestionnaire(arg.id).subscribe(() => {
          this.deleted.emit(this.questionnaire().id);
        });
      };
    });
  }

  onDelete(id: string) {
    this.questionnaire().steps = this.questionnaire().steps.filter(i => i.id !== id);
  }
}
