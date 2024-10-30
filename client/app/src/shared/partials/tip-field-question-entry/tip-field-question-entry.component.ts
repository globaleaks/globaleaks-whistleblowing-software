import { Component, EventEmitter, Injectable, Input, OnInit, Output } from '@angular/core';
import { FieldUtilitiesService } from '@app/shared/services/field-utilities.service';
import { NgbDateAdapter, NgbDateParserFormatter, NgbDateStruct } from '@ng-bootstrap/ng-bootstrap';


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

  @Output() validityChange = new EventEmitter<{ isValid: boolean; fieldId: string }>();

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
  isValid: boolean = false;

  constructor(private fieldUtilitiesService: FieldUtilitiesService){}


  ngOnInit(): void {

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

    this.onChange();
   
  }

  onChange(): void {
    const value = this.getValue();

    // Check if length is valid
    const meetsLength = this.isLengthValid(value);
    const meetsPattern = this.isPatternValid(value);

    // Check overall validity
    this.isValid = this.field.required
        ? !!value && meetsLength && meetsPattern
        : !value || (meetsLength && meetsPattern);

    // Notify parent component
    this.notifyValidity();
  }

  private getValue(): string {
    return this.fieldAnswers[this.field.id]?.[0]?.value || '';
  }

  // Check min and max length
  private isLengthValid(value: string): boolean {
    const minLength = this.field.attrs.min_len?.value;
    const maxLength = this.field.attrs.max_len?.value;
    const meetsMinLength = !minLength || value.length >= minLength;
    const meetsMaxLength = !maxLength || value.length <= maxLength;
    return meetsMinLength && meetsMaxLength;
  }

  // Check pattern validity
  private isPatternValid(value: string): boolean {
    if (!this.validator || !value) return true;
    const pattern = new RegExp(this.validator);
    return pattern.test(value);
  }

  onCheckboxChange(event: Event): void {
    this.isValid = this.field.required ? (event.target as HTMLInputElement).checked : true;
    this.notifyValidity();
  }

  onDataChange(): void {
    this.isValid = this.field.required ? !!this.dateRange.start && !!this.dateRange.end : true;
    this.notifyValidity();
  }

  notifyValidity(): void {
    this.validityChange.emit({ isValid: this.isValid, fieldId: this.field.id });
  }

  clearDateRange() {
    this.input_start_date = "";
    this.input_end_date = {year: 0, month: 0, day: 0};
    this.dateRange = {
      "start": "",
      "end": ""
    };

    this.field.value = "";
    this.onDataChange();
  }


  convertNgbDateToISOString(date: NgbDateStruct): string {
    const jsDate = new Date(date.year, date.month - 1, date.day);
    return jsDate.toISOString();
  }

  onStartDateSelection(date: NgbDateStruct): void {
    const startDate = new Date(date.year, date.month - 1, date.day);
    this.dateRange.start = startDate.getTime().toString();
    this.field.value = `${this.dateRange.start}:${this.dateRange.end}`;
    this.onDataChange();
  }

  onEndDateSelection(date: NgbDateStruct): void {
    const endDate = new Date(date.year, date.month - 1, date.day);
    this.dateRange.end = endDate.getTime().toString();
    this.field.value = `${this.dateRange.start}:${this.dateRange.end}`;
    this.onDataChange();
  }
}