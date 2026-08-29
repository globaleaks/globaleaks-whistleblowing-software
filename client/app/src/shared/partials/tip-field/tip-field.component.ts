import {Component, forwardRef, input} from "@angular/core";

import {TipFieldAnswerEntryComponent} from "../tip-field-answer-entry/tip-field-answer-entry.component";
import {TranslateModule} from "@ngx-translate/core";
import {OrderByPipe} from "@app/shared/pipes/order-by.pipe";

@Component({
    selector: "src-tip-field",
    templateUrl: "./tip-field.component.html",
    standalone: true,
    imports: [forwardRef(() => TipFieldAnswerEntryComponent), TranslateModule, OrderByPipe]
})
export class TipFieldComponent {
  readonly fields = input<any>();
  readonly index = input<number>();
  readonly fieldAnswers = input<any>();
  readonly preview = input(false);
  readonly redactMode = input<boolean>();
  readonly redactOperationTitle = input<string>();
  readonly disabled = input(false);

  hasMultipleEntries(field_answer: any): boolean {
    return Array.isArray(field_answer) && field_answer.length > 1;
  };
}
