import {Directive, HostListener} from "@angular/core";
import {AbstractControl, Validator, NG_VALIDATORS, ValidationErrors} from "@angular/forms";

@Directive({
    selector: "[customReceiptValidator]",
    providers: [{
            provide: NG_VALIDATORS,
            useExisting: ReceiptValidatorDirective,
            multi: true
        }],
    standalone: true
})
export class ReceiptValidatorDirective implements Validator {

  current_val = "";

  @HostListener("keyup", ["$event"])
  @HostListener("paste", ["$event"])
  @HostListener("keydown", ["$event"]) onKeyDown(e: KeyboardEvent) {
    const input = e.target as HTMLInputElement;
    input.value = this.current_val;
  }

  validate(control: AbstractControl): ValidationErrors | null {

    let result = "";
    if (control.value) {
      let viewValue = control.value.replace(/\D/g, "");

      while (viewValue.length) {
        result += viewValue.substring(0, 4);
        if (viewValue.length >= 4) {
          if (result.length < 19) {
            result += " ";
          }
          viewValue = viewValue.substring(4);
        } else {
          break;
        }
      }

      this.current_val = result.trim();

      if (result.length === 19) {
        return {"receiptvalidator": true};
      } else {
        return {"receiptvalidator": false};
      }
    }
    this.current_val = "";
    return {"receiptvalidator": true};
  }

}
