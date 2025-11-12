import {Component, Input, inject} from "@angular/core";
import {NgbModal} from "@ng-bootstrap/ng-bootstrap";
import {TranslateModule} from "@ngx-translate/core";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {NgClass} from "@angular/common";

interface AnswerHashInfo {
  fieldLabel: string;
  entryIndex: number;
  value: string;
  hash_sha256: string;
  hash_sha512: string;
}

@Component({
  selector: "src-questionnaire-answers-info",
  templateUrl: "./questionnaire-answers-info.component.html",
  standalone: true,
  imports: [TranslateModule, TranslatorPipe, NgClass]
})
export class QuestionnaireAnswersInfoComponent {
  private modalService = inject(NgbModal);

  @Input() answerHashes: AnswerHashInfo[] = [];

  cancel() {
    this.modalService.dismissAll();
  }
}

