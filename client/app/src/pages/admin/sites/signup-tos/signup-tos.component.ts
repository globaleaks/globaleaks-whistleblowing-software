import {Component, Input} from "@angular/core";
import {ControlContainer, NgForm, FormsModule} from "@angular/forms";
import {nodeResolverModel} from "@app/models/resolvers/node-resolver-model";

import {TranslateModule} from "@ngx-translate/core";

const TOS1_KEYS = {
  enable: "signup_tos1_enable",
  title: "signup_tos1_title",
  text: "signup_tos1_text",
  checkbox_label: "signup_tos1_checkbox_label"
} as const;

const TOS2_KEYS = {
  enable: "signup_tos2_enable",
  title: "signup_tos2_title",
  text: "signup_tos2_text",
  checkbox_label: "signup_tos2_checkbox_label"
} as const;

@Component({
    selector: "src-signup-tos",
    templateUrl: "./signup-tos.component.html",
    viewProviders: [{ provide: ControlContainer, useExisting: NgForm }],
    standalone: true,
    imports: [FormsModule, TranslateModule]
})
export class SignupTosComponent {
  @Input() node: nodeResolverModel;
  @Input() index: number;

  protected get keys() {
    return this.index === 2 ? TOS2_KEYS : TOS1_KEYS;
  }
}
