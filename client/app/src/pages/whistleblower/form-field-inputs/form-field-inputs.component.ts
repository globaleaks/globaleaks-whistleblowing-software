import {Component, forwardRef, OnInit, inject, input, output} from "@angular/core";
import {UtilsService} from "@app/shared/services/utils.service";
import {ControlContainer, NgForm} from "@angular/forms";
import {SubmissionService} from "@app/services/helper/submission.service";
import {Answers} from "@app/models/receiver/receiver-tip-data";
import {Step} from "@app/models/whistleblower/wb-tip-data";
import {Field} from "@app/models/resolvers/field-template-model";
import {NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
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
    forwardRef(() => FormFieldInputComponent),
    TranslateModule,
    TranslatorPipe,
    StripHtmlPipe
],
})
export class FormFieldInputsComponent implements OnInit {
  protected utilsService = inject(UtilsService);

  readonly field = input.required<Field>();
  readonly fieldRow = input<number>();
  readonly fieldCol = input<number>();
  readonly stepId = input<string>();
  readonly step = input<Step>();
  readonly entry = input<string>();
  readonly answers = input.required<Answers>();
  readonly submission = input<SubmissionService>();
  readonly index = input<number>();
  readonly displayErrors = input<boolean>();
  readonly fields = input<any>();
  readonly uploads = input<Record<string, any>>();
  readonly fileUploadUrl = input.required<string>();
  readonly fieldEntry = input<string>();
  readonly notifyFileUpload = output<any>();

  fieldId: string;
  fieldEntryId: string;
  entries: Record<string, Field>[] = [];

  ngOnInit(): void {
    const fieldEntry = this.fieldEntry();
    if(!fieldEntry){
      this.fieldId = this.stepId() + "-field-" + this.fieldRow() + "-" + this.fieldCol();
      this.fieldEntryId = this.fieldId + "-input-" + this.index();
    }else {
      this.fieldId = "-field-" + this.fieldRow() + "-" + this.fieldCol();
      this.fieldEntryId = fieldEntry + this.fieldId + "-input-" + this.index();
    }

    this.entries = this.getAnswersEntries(this.entry());

    if(!this.fieldEntryId){
      this.fieldEntryId = "";
    }
    this.indexAnswers(this.answers());
    this.indexAnswers(this.entries);
  }

  getAnswersEntries(entry: any) {
    if (typeof entry === "undefined") {
      return this.answers()[this.field().id];
    }

    return entry[this.field().id];
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

  indexAnswers(node: any): void {
    if (!node || typeof node !== 'object') return;
    for (const key of Object.keys(node)) {
      const arr = node[key];
      if (Array.isArray(arr)) {
        arr.forEach((entry, i) => {
          entry.index = `${i}`;
          for (const nestedKey of Object.keys(entry)) {
            if (Array.isArray(entry[nestedKey])) {
              entry[nestedKey].forEach((nestedItem, j) => {
                nestedItem.index = `${i}-${j}`;
              });
            }
          }
        });
      }
    }
  }

  addAnswerEntry(entries: any) {
    if (!Array.isArray(entries)) return;

    let newEntry = structuredClone(entries[0]);
    newEntry = this.resetEntries(newEntry);

    entries.push(newEntry);
    entries.forEach((entry, i) => {
      entry.index = `${i}`;
      for (const key in entry) {
        if (Array.isArray(entry[key])) {
          entry[key].forEach((nested, j) => {
            nested.index = `${i}-${j}`;
          });
        }
      }
    });
  }

}
