import {Component, forwardRef, OnInit, inject, input, output} from "@angular/core";
import {FieldUtilitiesService} from "@app/shared/services/field-utilities.service";
import {ControlContainer, NgForm, FormsModule} from "@angular/forms";
import {SubmissionService} from "@app/services/helper/submission.service";
import {NgbDateStruct, NgbInputDatepicker} from "@ng-bootstrap/ng-bootstrap";
import {Answers} from "@app/models/receiver/receiver-tip-data";
import {Step} from "@app/models/whistleblower/wb-tip-data";
import {Field} from "@app/models/resolvers/field-template-model";
import {NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {WhistleblowerIdentityFieldComponent} from "../fields/whistleblower-identity-field/whistleblower-identity-field.component";
import {NgSelectComponent, NgOptionComponent} from "@ng-select/ng-select";
import {MarkdownComponent} from "ngx-markdown";
import {VoiceRecorderComponent} from "@app/shared/partials/voice-recorder/voice-recorder.component";
import {RFileUploadButtonComponent} from "@app/shared/partials/rfile-upload-button/r-file-upload-button.component";
import {FormComponent} from "../form/form.component";
import {TranslateModule} from "@ngx-translate/core";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {StripHtmlPipe} from "@app/shared/pipes/strip-html.pipe";
import {OrderByPipe} from "@app/shared/pipes/order-by.pipe";
import {AutoExpandDirective} from "@app/shared/directive/auto-expand.directive";

@Component({
    selector: "src-form-field-input",
    templateUrl: "./form-field-input.component.html",
    viewProviders: [{ provide: ControlContainer, useExisting: NgForm }],
    standalone: true,
    imports: [AutoExpandDirective, FormsModule, forwardRef(() => WhistleblowerIdentityFieldComponent), NgbTooltipModule, NgSelectComponent, NgOptionComponent, NgbInputDatepicker, MarkdownComponent, VoiceRecorderComponent, RFileUploadButtonComponent, forwardRef(() => FormComponent), TranslateModule, TranslatorPipe, StripHtmlPipe, OrderByPipe]
})
export class FormFieldInputComponent implements OnInit {
  private fieldUtilitiesService = inject(FieldUtilitiesService);


  readonly field = input<any>();
  readonly index = input<number>();
  readonly step = input<Step>();
  readonly submission = input<SubmissionService>();
  readonly entryIndex = input<number>();
  readonly fieldEntry = input.required<string>();
  readonly entry = input<any>();
  readonly fieldId = input<string>();
  readonly displayErrors = input<boolean>();
  readonly answers = input.required<Answers>();
  readonly fields = input<Field>();
  readonly uploads = input<Record<string, any>>();
  readonly identity_provided = input<boolean>();
  readonly fileUploadUrl = input.required<string>();
  readonly notifyFileUpload = output<any>();

  fieldFormVarName: string;
  input_entryIndex = "";
  input_date: NgbDateStruct;
  input_start_date: any;
  input_end_date: NgbDateStruct;
  validator: string | RegExp;
  rows: Step;
  dateRange: { start: string, end: string } = {"start": "", "end": ""};
  dateOptions1: NgbDateStruct;
  dateOptions2: NgbDateStruct;
  dateOptions: {min_date:NgbDateStruct,max_date:NgbDateStruct}={min_date:{year:0,month:0,day:0},max_date:{year:0,month:0,day:0}}

  clearDateRange() {
    this.input_start_date = "";
    this.input_end_date = {year: 0, month: 0, day: 0};
    this.dateRange = {
      "start": "",
      "end": ""
    };
    this.entry().value = "";
  }

  initializeFormNames() {
    this.input_entryIndex = "input-" + this.entryIndex();
  }

  ngOnInit(): void {
    this.fieldFormVarName = this.fieldUtilitiesService.fieldFormName(this.field().id + "$" + this.index());
    this.initializeFormNames();
    this.rows = this.fieldUtilitiesService.splitRows(this.field().children);
    if (this.field().type === "inputbox") {
      const validator_regex = this.fieldUtilitiesService.getValidator(this.field());
      if (validator_regex.length > 0) {
        this.validator = validator_regex;
      }
    }
    if (this.field().type === "date") {
      if (this.field().attrs.min_date) {
        this.dateOptions.min_date = this.field().attrs.min_date.value;
      }
      if (this.field().attrs.max_date) {
        this.dateOptions.max_date = this.field().attrs.max_date.value;
      }
    }
    if (this.field().type === "daterange") {
      if (this.field().attrs.min_date) {
        this.dateOptions1 = this.field().attrs.min_date.value;
      }
      if (this.field().attrs.max_date) {
        this.dateOptions2 = this.field().attrs.max_date.value;
      }
    }
  }

  onDateSelection() {
    this.entry().value = this.convertNgbDateToISOString(this.input_date);
  }

  convertNgbDateToISOString(date: NgbDateStruct): string {
    const jsDate = new Date(date.year, date.month - 1, date.day);
    return jsDate.toISOString();
  }

  onStartDateSelection(date: NgbDateStruct): void {
    const startDate = new Date(date.year, date.month - 1, date.day);
    this.dateRange.start = startDate.getTime().toString();
    this.entry().value = `${this.dateRange.start}:${this.dateRange.end}`;
  }

  onEndDateSelection(date: NgbDateStruct): void {
    const endDate = new Date(date.year, date.month - 1, date.day);
    this.dateRange.end = endDate.getTime().toString();
    this.entry().value = `${this.dateRange.start}:${this.dateRange.end}`;
  }

  validateUploadSubmission() {
    const uploads = this.uploads();
    return !!(uploads && uploads[this.field() ? this.field().id : "status_page"] !== undefined && (this.field().type === "fileupload" && uploads && uploads[this.field() ? this.field().id : "status_page"] && Object.keys(uploads[this.field() ? this.field().id : "status_page"]).length === 0));
  }

}
