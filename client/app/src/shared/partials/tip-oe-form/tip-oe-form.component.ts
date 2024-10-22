import {Component, EventEmitter, Input, Output} from "@angular/core";

@Component({
  selector: "src-tip-oe-form",
  templateUrl: "./tip-oe-form.component.html"
})
export class TipOeFormComponent{

  @Input() fields: any;
  
  @Output() notifyFileUpload: EventEmitter<any> = new EventEmitter<any>();

  @Output() sumbitFormEvent: EventEmitter<any> = new EventEmitter<any>();

  @Input() tipStatus: string = 'opened';

  @Input() fieldAnswers: any;

  @Input() displayErrors: boolean;

  @Input() fileUploadUrl: string;



  validateUploadSubmission() {
    // return !!(this.uploads && this.uploads[this.field ? this.field.id : "status_page"] !== undefined && (this.field.type === "fileupload" && this.uploads && this.uploads[this.field ? this.field.id : "status_page"] && Object.keys(this.uploads[this.field ? this.field.id : "status_page"]).length === 0));
  }

  exampleNotify(event: any){
    console.log("example notify in tipOEForm")
    this.notifyFileUpload.emit(event);
  }

  onSubmit() { 
    console.log("onSubmit");
    debugger

    this.sumbitFormEvent.emit();
    
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


