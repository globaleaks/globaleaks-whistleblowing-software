import {Component, Input} from "@angular/core";
import { Children3 } from "@app/models/reciever/reciever-tip-data";

@Component({
  selector: "src-tip-oe-form",
  templateUrl: "./tip-oe-form.component.html"
})
export class TipOeFormComponent {
  @Input() fields: Children3[];

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
