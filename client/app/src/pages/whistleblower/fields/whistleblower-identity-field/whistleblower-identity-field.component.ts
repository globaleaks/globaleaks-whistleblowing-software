import {Component, forwardRef, OnInit, input, output} from "@angular/core";
import {ControlContainer, NgForm} from "@angular/forms";
import {Answers} from "@app/models/receiver/receiver-tip-data";
import {Field} from "@app/models/resolvers/field-template-model";
import {Step} from "@app/models/whistleblower/wb-tip-data";
import {SubmissionService} from "@app/services/helper/submission.service";

import {FormComponent} from "../../form/form.component";
import {FormsModule} from '@angular/forms';
import {TranslateModule} from "@ngx-translate/core";

@Component({
    selector: "src-whistleblower-identity-field",
    templateUrl: "./whistleblower-identity-field.component.html",
    viewProviders: [{ provide: ControlContainer, useExisting: NgForm }],
    standalone: true,
    imports: [forwardRef(() => FormComponent), FormsModule, TranslateModule]
})
export class WhistleblowerIdentityFieldComponent implements OnInit {
  readonly submission = input<SubmissionService>();
  readonly field = input.required<Field>();
  readonly stateChanged = output<boolean>();
  readonly notifyFileUpload = output<any>();
  readonly stepId = input<string>();
  readonly fieldCol = input<number>();
  readonly fieldRow = input<number>();
  readonly index = input<number>();
  readonly step = input.required<Step>();
  readonly answers = input.required<Answers>();
  readonly entry = input<string>();
  readonly fields = input<Field>();
  readonly displayErrors = input<boolean>();
  readonly uploads = input<Record<string, any>>();
  readonly fileUploadUrl = input.required<string>();

  identity_provided = true;

  ngOnInit(): void {
    this.stateChanged.emit(true);
    const submission = this.submission();
    if (submission) {
      submission.submission.identity_provided = true;
    }
  }

  changeIdentitySetting(status: boolean): void {
    this.identity_provided = status;
    const submission = this.submission();
    if (submission) {
      submission.submission.identity_provided = status;
    }
    this.stateChanged.emit(status);
  }
}
