import {Component, EventEmitter, Input, Output} from "@angular/core";
import { NgForm } from "@angular/forms";
import { FieldUtilitiesService } from "@app/shared/services/field-utilities.service";

@Component({
  selector: "src-tip-eo-form",
  templateUrl: "./tip-eo-form.component.html"
})
export class TipEoFormComponent{

  @Input() fields: any;
  
  @Output() sumbitFormEvent: EventEmitter<any> = new EventEmitter<any>();

  @Input() tipStatus: string = 'opened';

  @Input() fieldAnswers: any;

  @Input() displayErrors: boolean;

  isFormValid: boolean = false;
  private fieldValidityMap = new Map<string, boolean>();

  constructor(private fieldUtilitiesService: FieldUtilitiesService){}

  private updateFormValidity(): void {
    this.isFormValid = Array.from(this.fieldValidityMap.values()).every(value => value === true);
  }

  onFieldValidityChange(isValid: boolean, fieldId: string): void {
    this.fieldValidityMap.set(fieldId, isValid);
    this.updateFormValidity();
  }

  onSubmit() {
    this.sumbitFormEvent.emit();  
  }

  onFormChange(){
    this.fieldUtilitiesService.onAnswersUpdate(this);
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


