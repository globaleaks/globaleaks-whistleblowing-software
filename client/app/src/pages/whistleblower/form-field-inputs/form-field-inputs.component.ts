import {Component, EventEmitter, forwardRef, Input, OnInit, Output, inject} from "@angular/core";
import {UtilsService} from "@app/shared/services/utils.service";
import {ControlContainer, NgForm} from "@angular/forms";
import {SubmissionService} from "@app/services/helper/submission.service";
import {Answers} from "@app/models/receiver/receiver-tip-data";
import {Step} from "@app/models/whistleblower/wb-tip-data";
import {Field} from "@app/models/resolvers/field-template-model";
import {cloneDeep} from "lodash-es";
import {NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {NgClass} from "@angular/common";
import {MarkdownComponent} from "ngx-markdown";
import {FormFieldInputComponent} from "../form-field-input/form-field-input.component";
import {TranslateModule} from "@ngx-translate/core";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {StripHtmlPipe} from "@app/shared/pipes/strip-html.pipe";

@Component({
    selector: "src-form-field-inputs",
    templateUrl: "./form-field-inputs.component.html",
    viewProviders: [{ provide: ControlContainer, useExisting: NgForm }],
    standalone: true,
    imports: [
    MarkdownComponent,
    NgbTooltipModule,
    NgClass,
    forwardRef(() => FormFieldInputComponent),
    TranslateModule,
    TranslatorPipe,
    StripHtmlPipe
],
})
export class FormFieldInputsComponent implements OnInit {
  protected utilsService = inject(UtilsService);

  @Input() field: Field;
  @Input() fieldRow: number;
  @Input() fieldCol: number;
  @Input() stepId: string;
  @Input() step: Step;
  @Input() entry: string;
  @Input() answers: Answers;
  @Input() submission: SubmissionService;
  @Input() index: number;
  @Input() displayErrors: boolean;
  @Input() fields: any;
  @Input() uploads: { [key: string]: any };
  @Input() identity_provided: boolean;
  @Input() fileUploadUrl: string;
  @Input() fieldEntry: string;
  @Output() notifyFileUpload: EventEmitter<any> = new EventEmitter<any>();

  fieldId: string;
  entries: { [key: string]: Field }[] = [];

  ngOnInit(): void {
    if(!this.fieldEntry){
      this.fieldId = this.stepId + "-field-" + this.fieldRow + "-" + this.fieldCol;
      this.fieldEntry = this.fieldId + "-input-" + this.index;
    }else {
      this.fieldId = "-field-" + this.fieldRow + "-" + this.fieldCol;
      this.fieldEntry += this.fieldId + "-input-" + this.index;
    }

    this.entries = this.getAnswersEntries(this.entry);

    if(!this.fieldEntry){
      this.fieldEntry = "";
    }
  }

  getAnswersEntries(entry: any) {
    if (typeof entry === "undefined") {
      return this.answers[this.field.id];
    }

    return entry[this.field.id];
  };

  resetEntries(obj: any) {
    if (typeof obj === "boolean") {
      return false;
    } else if (typeof obj === "string") {
      return "";
    } else if (Array.isArray(obj)) {
      for (let i = 0; i < obj.length; i++) {
        obj[i] = this.resetEntries(obj[i]);
      }
    } else if (typeof obj === "object") {
      for (const key in obj) {
        if (Object.prototype.hasOwnProperty.call(obj, key)) {
          obj[key] = this.resetEntries(obj[key]);
        }
      }
    }
    return obj;
  }

  addAnswerEntry(entries:any) {
    let newEntry = cloneDeep(entries[0]);
    newEntry = this.resetEntries(newEntry)
    entries.push(newEntry);
  };

}
