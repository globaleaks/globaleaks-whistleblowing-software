import {Component, inject} from "@angular/core";
import {NgbModal} from "@ng-bootstrap/ng-bootstrap";
import {questionnaireResolverModel} from "@app/models/resolvers/questionnaire-model";
import {HttpService} from "@app/shared/services/http.service";
import {FormsModule} from "@angular/forms";
import {TranslateModule} from "@ngx-translate/core";

@Component({
    selector: "src-questionnaire-duplication",
    templateUrl: "./questionnaire-duplication.component.html",
    standalone: true,
    imports: [FormsModule, TranslateModule]
})
export class QuestionnaireDuplicationComponent {
  private httpService = inject(HttpService);
  private modalService = inject(NgbModal);

  questionnaire: questionnaireResolverModel;
  operation: string;
  confirmFunction: () => void;
  duplicate_questionnaire: { name: string } = {name: ""};

  cancel() {
    this.modalService.dismissAll();
  }

  confirm() {
    if (this.operation === "duplicate" && this.duplicate_questionnaire.name.length > 0) {
      this.httpService.requestDuplicateAdminQuestionnaire(
        {
          questionnaire_id: this.questionnaire.id,
          new_name: this.duplicate_questionnaire.name
        }
      ).subscribe(() => {
        this.modalService.dismissAll();
        this.confirmFunction();
      });
    } else {
      this.modalService.dismissAll();
    }
  }
}
