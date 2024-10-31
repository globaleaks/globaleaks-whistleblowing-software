import {Component, Input, OnChanges, SimpleChanges} from "@angular/core";
import {NgClass} from "@angular/common";

@Component({
    selector: "src-password-meter",
    templateUrl: "./password-meter.component.html",
    standalone: true,
    imports: [NgClass]
})
export class PasswordMeterComponent implements OnChanges {

  @Input() passwordStrengthScore = 0;
  strengthType: string = "";
  strengthText: string = "";

  ngOnChanges(_: SimpleChanges): void {
    if (this.passwordStrengthScore < 2) {
      this.strengthType = "bg-danger";
      this.strengthText = "Weak";
    } else if (this.passwordStrengthScore < 3) {
      this.strengthType = "bg-warning";
      this.strengthText = "Acceptable";
    } else {
      this.strengthType = "bg-primary";
      this.strengthText = "Strong";
    }
  }
}
