import {Component, OnChanges, SimpleChanges, input} from "@angular/core";

@Component({
    selector: "src-password-meter",
    templateUrl: "./password-meter.component.html",
    standalone: true,
    imports: []
})
export class PasswordMeterComponent implements OnChanges {

  readonly passwordStrengthScore = input(0);
  strengthType = "";
  strengthText = "";

  ngOnChanges(_: SimpleChanges): void {
    if (this.passwordStrengthScore() < 2) {
      this.strengthType = "bg-danger";
      this.strengthText = "Weak";
    } else if (this.passwordStrengthScore() < 3) {
      this.strengthType = "bg-warning";
      this.strengthText = "Acceptable";
    } else {
      this.strengthType = "bg-primary";
      this.strengthText = "Strong";
    }
  }
}
