import {Component, EventEmitter, forwardRef, Input, OnInit, Output} from "@angular/core";
import {ControlContainer, NgForm} from "@angular/forms";
import {Answers} from "@app/models/reciever/reciever-tip-data";
import {Field} from "@app/models/resolvers/field-template-model";
import {Step} from "@app/models/whistleblower/wb-tip-data";
import {SubmissionService} from "@app/services/helper/submission.service";

import { FormComponent } from "../../form/form.component";
import { TranslateModule } from "@ngx-translate/core";
import { TranslatorPipe } from "@app/shared/pipes/translate";

@Component({
    selector: "src-whistleblower-identity-field",
    templateUrl: "./whistleblower-identity-field.component.html",
    viewProviders: [{ provide: ControlContainer, useExisting: NgForm }],
    standalone: true,
    imports: [forwardRef(() => FormComponent), TranslateModule, TranslatorPipe]
})
export class WhistleblowerIdentityFieldComponent implements OnInit {
  @Input() submission: SubmissionService;
  @Input() field: Field;
  @Output() stateChanged = new EventEmitter<boolean>();
  @Output() notifyFileUpload: EventEmitter<any> = new EventEmitter<any>();
  @Input() stepId: string;
  @Input() fieldCol: number;
  @Input() fieldRow: number;
  @Input() index: number;
  @Input() step: Step;
  @Input() answers: Answers;
  @Input() entry: string;
  @Input() fields: Field;
  @Input() displayErrors: boolean;
  @Input() identity_provided: boolean = false;
  @Input() uploads: { [key: string]: any };
  @Input() fileUploadUrl: string;
  
  ngOnInit(): void {
    this.identity_provided = true;
    this.stateChanged.emit(true);
    if (this.submission) {
      this.submission.submission.identity_provided = true;
    }
  }

  changeIdentitySetting(status: boolean): void {
    this.identity_provided = status;
    if (this.submission) {
      this.submission.submission.identity_provided = status;
    }
    this.stateChanged.emit(status);
  }
}
