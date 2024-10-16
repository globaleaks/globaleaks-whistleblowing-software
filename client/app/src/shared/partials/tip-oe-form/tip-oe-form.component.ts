import {Component, EventEmitter, Injectable, Input, OnInit, Output} from "@angular/core";
import { Step } from "@app/models/app/shared-public-model";
import { NgbDateAdapter, NgbDateParserFormatter, NgbDateStruct } from "@ng-bootstrap/ng-bootstrap";


/**
 * This Service handles how the date is represented in scripts i.e. ngModel.
 */
@Injectable()
export class CustomAdapter extends NgbDateAdapter<string> {

	fromModel(value: string | null): NgbDateStruct | null {
		if (value) {
			const date = new Date (value);
			return {
				day: date.getUTCDate() ,
				month: date.getUTCMonth() + 1,
				year: date.getUTCFullYear(),
			};
		}
		return null;
	}

	toModel(date: NgbDateStruct | null): string | null {
		if (date){
      const utcDate = Date.UTC(date.year, date.month - 1, date.day);
      const jsDate = new Date(utcDate);
      return jsDate.toISOString();
    }
    else 
      return null;
	}
}

/**
 * This Service handles how the date is rendered and parsed from keyboard i.e. in the bound input field.
 */
@Injectable()
export class CustomDateParserFormatter extends NgbDateParserFormatter {
	readonly DELIMITER = '/';

	parse(value: string): NgbDateStruct | null {
		if (value) {
			const date = value.split(this.DELIMITER);
			return {
				day: parseInt(date[0], 10),
				month: parseInt(date[1], 10),
				year: parseInt(date[2], 10),
			};
		}
		return null;
	}

	format(date: NgbDateStruct | null): string {

    if (date){
      return String(date.day).padStart(2,"0") + this.DELIMITER + String(date.month).padStart(2,"0") + this.DELIMITER + date.year;
    }
    else 
      return  '';
	}
}



@Component({
  selector: "src-tip-oe-form",
  templateUrl: "./tip-oe-form.component.html",
  providers: [
		{ provide: NgbDateAdapter, useClass: CustomAdapter },
		{ provide: NgbDateParserFormatter, useClass: CustomDateParserFormatter },
	]
})
export class TipOeFormComponent implements OnInit{

  @Input() fields: any;
  @Input() uploads: { [key: string]: any };
  @Input() fileUploadUrl: string;
  @Input() campo: any;
  @Input() index: number;
  @Input() step: Step;
  @Input() fieldEntry: string;
  @Input() entryIndex: number;
  // @Input() submission: SubmissionService;
  @Output() notifyFileUpload: EventEmitter<any> = new EventEmitter<any>();

  @Input() tipStatus: string = 'opened';

  @Input() fieldAnswers: any;

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

  ngOnInit(): void {
    throw new Error("Method not implemented.");
  }


  onDateSelection(value: NgbDateStruct, field: any) {

    field.value = this.convertNgbDateToISOString(value);
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


