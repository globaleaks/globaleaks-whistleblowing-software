import {Component, forwardRef, OnInit, inject, input, output} from "@angular/core";
import {FieldUtilitiesService} from "@app/shared/services/field-utilities.service";
import {ControlContainer, NgForm} from "@angular/forms";
import {SubmissionService} from "@app/services/helper/submission.service";
import {Answers} from "@app/models/receiver/receiver-tip-data";
import {Children, Step} from "@app/models/whistleblower/wb-tip-data";
import {FormFieldInputsComponent} from "../form-field-inputs/form-field-inputs.component";
import {OrderByPipe} from "@app/shared/pipes/order-by.pipe";

@Component({
    selector: "src-form",
    templateUrl: "./form.component.html",
    viewProviders: [{ provide: ControlContainer, useExisting: NgForm }],
    standalone: true,
    imports: [
    forwardRef(() => FormFieldInputsComponent),
    OrderByPipe
],
})
export class FormComponent implements OnInit {
  protected fieldUtilitiesService = inject(FieldUtilitiesService);

  readonly step = input.required<Step>();
  readonly index = input<number>();
  readonly answers = input.required<Answers>();
  readonly uploads = input<Record<string, any>>();
  readonly submission = input<SubmissionService>();
  readonly displayErrors = input<boolean>();
  readonly entry = input<string>();
  readonly fileUploadUrl = input.required<string>();
  readonly notifyFileUpload = output<any>();
  readonly fieldEntry = input("");

  fields: Children[];
  stepId: string;
  rows: any;
  status: { opened: boolean };

  ngOnInit(): void {
    this.initialize();
  }

  initialize() {
    const step = this.step();
    if (step.children) {
      this.fields = step.children;
      this.rows = this.fieldUtilitiesService.splitRows(this.fields);
    } else {
      this.fields = [];
      this.rows = step;
    }
    this.stepId = "step-" + this.index();
    this.status = {
      opened: false,
    };
  }
}
