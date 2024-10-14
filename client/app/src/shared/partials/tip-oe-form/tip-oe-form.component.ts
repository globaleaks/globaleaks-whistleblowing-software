import {Component, EventEmitter, Input, Output} from "@angular/core";
import { Step } from "@app/models/app/shared-public-model";
import { Children3 } from "@app/models/reciever/reciever-tip-data";
import { Field } from "@app/models/resolvers/field-template-model";
import { NgbDateStruct } from "@ng-bootstrap/ng-bootstrap";

@Component({
  selector: "src-tip-oe-form",
  templateUrl: "./tip-oe-form.component.html"
})
export class TipOeFormComponent {
  @Input() fields: Children3[];
  @Input() uploads: { [key: string]: any };
  @Input() fileUploadUrl: string;
  @Input() campo: any;
  @Input() index: number;
  @Input() step: Step;
  @Input() fieldEntry: string;
  @Input() entryIndex: number;
  // @Input() submission: SubmissionService;
  @Output() notifyFileUpload: EventEmitter<any> = new EventEmitter<any>();

  input_date: NgbDateStruct;
  input_start_date: any;
  input_end_date: NgbDateStruct;
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
    // this.entry.value = "";
  }


  onDateSelection() {
    // this.entry.value = this.convertNgbDateToISOString(this.input_date);
  }

  convertNgbDateToISOString(date: NgbDateStruct): string {
    const jsDate = new Date(date.year, date.month - 1, date.day);
    return jsDate.toISOString();
  }

  onStartDateSelection(date: NgbDateStruct): void {
    const startDate = new Date(date.year, date.month - 1, date.day);
    this.dateRange.start = startDate.getTime().toString();
    // this.entry.value = `${this.dateRange.start}:${this.dateRange.end}`;
  }

  onEndDateSelection(date: NgbDateStruct): void {
    const endDate = new Date(date.year, date.month - 1, date.day);
    this.dateRange.end = endDate.getTime().toString();
    // this.entry.value = `${this.dateRange.start}:${this.dateRange.end}`;
  }

  validateUploadSubmission() {
    // return !!(this.uploads && this.uploads[this.field ? this.field.id : "status_page"] !== undefined && (this.field.type === "fileupload" && this.uploads && this.uploads[this.field ? this.field.id : "status_page"] && Object.keys(this.uploads[this.field ? this.field.id : "status_page"]).length === 0));
  }


  htmlType(type: string): string{
    switch(type){
      case "inputbox":
        return "text";
      
      case "selectbox":
        return "select";

      default:
        return "text";
    }
  }
}
