import {Directive, Input, Output, EventEmitter} from "@angular/core";
import {NG_VALIDATORS, AbstractControl, Validator, ValidationErrors} from "@angular/forms";

@Directive({
    selector: "[passwordStrengthValidator]",
    providers: [{
            provide: NG_VALIDATORS,
            useExisting: PasswordStrengthValidatorDirective,
            multi: true
        }],
    standalone: true
})
export class PasswordStrengthValidatorDirective implements Validator {
  @Input("passwordStrengthValidator") passwordStrength: string;
  @Output() passwordStrengthChange = new EventEmitter<number>();

  validate(control: AbstractControl): ValidationErrors | null {
    const pwd = control.value;

    const types: {
      lower: boolean;
      upper: boolean;
      symbols: boolean;
      digits: boolean;
    } = {
      lower: /[a-z]/.test(pwd),
      upper: /[A-Z]/.test(pwd),
      symbols: /\W/.test(pwd),
      digits: /\d/.test(pwd)
    };

    let variation1 = 0;
    let variation2 = 0;
    const letters: { [key: string]: number } = {};
    let score = 0;

    if (pwd) {
      /* Score symbols variation */
      for (const type in types) {
        if (Object.prototype.hasOwnProperty.call(types, type)) {
          variation1 += (types as Record<string, boolean>)[type] ? 1 : 0;
        }
      }

      /* Score unique symbols */
      for (let i = 0; i < pwd.length; i++) {
        if (!letters[pwd[i]]) {
          letters[pwd[i]] = 1;
          variation2 += 1;
        }
      }

      if (variation1 !== 4 || variation2 < 10 || pwd.length < 12) {
        score = 1;
      } else if (variation1 !== 4 || variation2 < 12 || pwd.length < 14) {
        score = 2;
      } else {
        score = 3;
      }
    }

    if (control) {
      this.passwordStrengthChange.emit(score);
    }

    return score > 1 ? null : {passwordStrengthValidator: true};
  }
}