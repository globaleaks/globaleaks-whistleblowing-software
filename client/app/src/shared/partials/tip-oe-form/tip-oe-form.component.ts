import {Component, EventEmitter, Input, Output} from "@angular/core";
import { Step } from "@app/models/app/shared-public-model";
import { NgbDateStruct } from "@ng-bootstrap/ng-bootstrap";


@Component({
  selector: "src-tip-oe-form",
  templateUrl: "./tip-oe-form.component.html"
})
export class TipOeFormComponent{

  @Input() fields: any;
  // @Input() submission: SubmissionService;
  @Output() notifyFileUpload: EventEmitter<any> = new EventEmitter<any>();

  @Input() tipStatus: string = 'opened';

  @Input() fieldAnswers: any;

  @Input() displayErrors: boolean;

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


