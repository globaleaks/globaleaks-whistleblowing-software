import {Component, EventEmitter, forwardRef, Input, OnInit, Output, inject} from "@angular/core";
import {FieldUtilitiesService} from "@app/shared/services/field-utilities.service";
import {ControlContainer, NgForm} from "@angular/forms";
import {SubmissionService} from "@app/services/helper/submission.service";
import {Answers} from "@app/models/receiver/receiver-tip-data";
import {Children, Step} from "@app/models/whistleblower/wb-tip-data";
import {NgClass} from "@angular/common";
import {FormFieldInputsComponent} from "../form-field-inputs/form-field-inputs.component";
import {OrderByPipe} from "@app/shared/pipes/order-by.pipe";

@Component({
    selector: "src-form",
    templateUrl: "./form.component.html",
    viewProviders: [{ provide: ControlContainer, useExisting: NgForm }],
    standalone: true,
    imports: [
    NgClass,
    forwardRef(() => FormFieldInputsComponent),
    OrderByPipe
],
})
export class FormComponent implements OnInit {
  protected fieldUtilitiesService = inject(FieldUtilitiesService);

  @Input() step: Step;
  @Input() index: number;
  @Input() answers: Answers;
  @Input() uploads: { [key: string]: any };
  @Input() submission: SubmissionService;
  @Input() displayErrors: boolean;
  @Input() entry: string;
  @Input() identity_provided: any;
  @Input() fileUploadUrl: string;
  @Output() notifyFileUpload: EventEmitter<any> = new EventEmitter<any>();
  @Input() fieldEntry: string;

  fields: Children[];
  stepId: string;
  rows: any;
  status: { opened: boolean };

  ngOnInit(): void {
    this.initialize();
  }

  initialize() {
    if (this.step.children) {
      this.fields = this.step.children;
    } else {
      this.fields = [];
    }
    this.stepId = "step-" + this.index;
    this.rows = this.fieldUtilitiesService.splitRows(this.fields);
    if (this.rows.length === 0) {
      this.rows = this.step;
    }
    this.status = {
      opened: false,
    };
  }
}
