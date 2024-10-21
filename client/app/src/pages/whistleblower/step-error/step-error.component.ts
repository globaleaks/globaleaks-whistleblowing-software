import {Component, EventEmitter, Input, Output, QueryList} from "@angular/core";
import {FormArray, FormGroup, NgForm} from "@angular/forms";
import {Field} from "@app/models/resolvers/field-template-model";
import {DisplayStepErrorsFunction, StepFormFunction} from "@app/shared/constants/types";

import { StepErrorEntryComponent } from "./template/step-error-entry/step-error-entry.component";
import { TranslateModule } from "@ngx-translate/core";
import { TranslatorPipe } from "@app/shared/pipes/translate";

@Component({
    selector: "src-step-error",
    templateUrl: "./step-error.component.html",
    standalone: true,
    imports: [StepErrorEntryComponent, TranslateModule, TranslatorPipe]
})
export class StepErrorComponent {
  @Input() navigation: number;
  @Input() stepForm: NgForm;
  @Input() field_id_map: { [key: string]: Field };
  @Output() goToStep: EventEmitter<any> = new EventEmitter();

  getInnerGroupErrors(form: NgForm): string[] {
    const errors: string[] = [];
    this.processFormGroup(form.form, errors);
    return errors;
  }

  private processFormGroup(formGroup: FormGroup, errors: string[], parentControlName = ""): void {
    Object.keys(formGroup.controls).forEach(controlName => {
      const control = formGroup.controls[controlName];

      if (control instanceof FormGroup) {
        const nestedControlName = parentControlName ? `${parentControlName}.${controlName}` : controlName;
        this.processFormGroup(control, errors, nestedControlName);
      } else if (control instanceof FormArray) {
        control.controls.forEach((nestedControl, index) => {
          const nestedControlName = parentControlName ? `${parentControlName}.${controlName}[${index}]` : `${controlName}[${index}]`;
          this.processFormGroup(nestedControl as FormGroup, errors, nestedControlName);
        });
      } else if (control.errors) {
        errors.push(parentControlName);
      }
    });
  }
}
