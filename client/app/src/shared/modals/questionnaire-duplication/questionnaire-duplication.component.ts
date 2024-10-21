import {HttpClient} from "@angular/common/http";
import { Component, Input, inject } from "@angular/core";
import {NgbModal} from "@ng-bootstrap/ng-bootstrap";
import {UtilsService} from "@app/shared/services/utils.service";
import {questionnaireResolverModel} from "@app/models/resolvers/questionnaire-model";
import { FormsModule } from "@angular/forms";
import { TranslateModule } from "@ngx-translate/core";
import { TranslatorPipe } from "@app/shared/pipes/translate";

@Component({
    selector: "src-questionnaire-duplication",
    templateUrl: "./questionnaire-duplication.component.html",
    standalone: true,
    imports: [FormsModule, TranslateModule, TranslatorPipe]
})
export class QuestionnaireDuplicationComponent {
  private utilsService = inject(UtilsService);
  private http = inject(HttpClient);
  private modalService = inject(NgbModal);

  @Input() questionnaire: questionnaireResolverModel;
  @Input() operation: string;
  duplicate_questionnaire: { name: string } = {name: ""};

  cancel() {
    this.modalService.dismissAll();
  }

  confirm() {
    if (this.operation === "duplicate" && this.duplicate_questionnaire.name.length > 0) {
      this.http.post(
        "api/admin/questionnaires/duplicate",
        {
          questionnaire_id: this.questionnaire.id,
          new_name: this.duplicate_questionnaire.name
        }
      ).subscribe(() => {
        this.modalService.dismissAll();
        this.utilsService.reloadComponent();
      });
    } else {
      this.modalService.dismissAll();
    }
  }
}
