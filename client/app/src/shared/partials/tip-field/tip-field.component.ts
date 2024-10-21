import {Component, forwardRef, Input} from "@angular/core";

import { TipFieldAnswerEntryComponent } from "../tip-field-answer-entry/tip-field-answer-entry.component";
import { TranslateModule } from "@ngx-translate/core";
import { TranslatorPipe } from "@app/shared/pipes/translate";
import { OrderByPipe } from "@app/shared/pipes/order-by.pipe";

@Component({
    selector: "src-tip-field",
    templateUrl: "./tip-field.component.html",
    standalone: true,
    imports: [forwardRef(() => TipFieldAnswerEntryComponent), TranslateModule, TranslatorPipe, OrderByPipe]
})
export class TipFieldComponent {
  @Input() fields: any;
  @Input() index: number;
  @Input() fieldAnswers: any;
  @Input() preview: boolean = false;
  @Input() redactMode: boolean;
  @Input() redactOperationTitle: string;

  hasMultipleEntries(field_answer: any): boolean {
    return Array.isArray(field_answer) && field_answer.length > 1;
  };
}
