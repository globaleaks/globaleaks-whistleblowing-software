import { Component, EventEmitter, Injectable, Input, OnInit, Output } from '@angular/core';
import { NgForm } from '@angular/forms';
import { FieldUtilitiesService } from '@app/shared/services/field-utilities.service';
import { NgbDateAdapter, NgbDateParserFormatter, NgbDateStruct } from '@ng-bootstrap/ng-bootstrap';
import { AnyCatcher } from 'rxjs/internal/AnyCatcher';

/**
 * This Service handles how the date is represented in scripts i.e. ngModel.
 */
@Injectable()
export class CustomAdapter extends NgbDateAdapter<string> {

	fromModel(value: string | null): NgbDateStruct | null {
		if (value) {
			const date = new Date(value);
			return {
				day: date.getDate(),
				month: date.getMonth() + 1,
				year: date.getFullYear(),
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
  selector: 'src-tip-field-question-entry',
  templateUrl: './tip-field-question-entry.component.html',
  providers: [
		{ provide: NgbDateAdapter, useClass: CustomAdapter },
		{ provide: NgbDateParserFormatter, useClass: CustomDateParserFormatter },
	]
})
export class TipFieldQuestionEntryComponent implements OnInit{

  @Output() notifyFileUpload: EventEmitter<any> = new EventEmitter<any>();
  @Input() fileUploadUrl: string;

  @Input() editField: NgForm;

  @Input() field: any;
  @Input() fieldAnswers: any;
  @Input() displayErrors: boolean;

  input_start_date: any;
  input_end_date: any;
  dateRange: { start: string, end: string } = {"start": "", "end": ""};
  dateOptions1: NgbDateStruct;
  dateOptions2: NgbDateStruct;
  dateOptions: {min_date:NgbDateStruct,max_date:NgbDateStruct}={min_date:{year:0,month:0,day:0},max_date:{year:0,month:0,day:0}}

  validator: string | RegExp;

  uploads: { [key: string]: any } = {};

  constructor(private fieldUtilitiesService: FieldUtilitiesService){}


  ngOnInit(): void {

    console.log(JSON.stringify(this.field))

   if(this.field.type==='daterange' && this.fieldAnswers[this.field.id][0].value){
    this.input_start_date = new Date().setTime(this.fieldAnswers[this.field.id][0].value.split(":")[0]);
    this.input_end_date = new Date().setTime(this.fieldAnswers[this.field.id][0].value.split(":")[1]);
   }

   if (this.field.type === "inputbox") {
    const validator_regex = this.fieldUtilitiesService.getValidator(this.field);
    if (validator_regex.length > 0) {
      this.validator = validator_regex;
    }
  }
   
  }


  testEvent(event: any){
    //TODO: rinominare metodo
    this.notifyFileUpload.emit(event)
  }


  clearDateRange() {
    this.input_start_date = "";
    this.input_end_date = {year: 0, month: 0, day: 0};
    this.dateRange = {
      "start": "",
      "end": ""
    };

    this.field.value = "";
  }


  convertNgbDateToISOString(date: NgbDateStruct): string {
    const jsDate = new Date(date.year, date.month - 1, date.day);
    return jsDate.toISOString();
  }

  onStartDateSelection(date: NgbDateStruct): void {
    console.log(this.editField)
    console.log(this.editField.form.get(this.field.id))
    const startDate = new Date(date.year, date.month - 1, date.day);
    this.dateRange.start = startDate.getTime().toString();
    this.field.value = `${this.dateRange.start}:${this.dateRange.end}`;
  }

  onEndDateSelection(date: NgbDateStruct): void {
    const endDate = new Date(date.year, date.month - 1, date.day);
    this.dateRange.end = endDate.getTime().toString();
    this.field.value = `${this.dateRange.start}:${this.dateRange.end}`;
  }

  validateUploadSubmission() {
    // return !!(this.uploads && this.uploads[this.field ? this.field.id : "status_page"] !== undefined && (this.field.type === "fileupload" && this.uploads && this.uploads[this.field ? this.field.id : "status_page"] && Object.keys(this.uploads[this.field ? this.field.id : "status_page"]).length === 0));
  }
  
}
