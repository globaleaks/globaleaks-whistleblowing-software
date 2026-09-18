import {Component, inject, input} from "@angular/core";
import {AppDataService} from "@app/app-data.service";
import {ControlContainer, NgForm, FormsModule} from "@angular/forms";
import {Signup} from "@app/models/component-model/signup";

import {MarkdownComponent} from "ngx-markdown";
import {StripHtmlPipe} from "@app/shared/pipes/strip-html.pipe";

@Component({
    selector: "src-tos",
    templateUrl: "./tos.component.html",
    viewProviders: [{ provide: ControlContainer, useExisting: NgForm }],
    standalone: true,
    imports: [FormsModule, MarkdownComponent, StripHtmlPipe]
})
export class TosComponent {
  protected appDataService = inject(AppDataService);

  readonly signup = input.required<Signup>();
  readonly signupform = input<NgForm>();
}
