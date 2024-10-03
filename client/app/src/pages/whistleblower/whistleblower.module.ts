import {NgModule} from "@angular/core";
import {CommonModule, NgOptimizedImage} from "@angular/common";
import {HomepageComponent} from "@app/pages/whistleblower/homepage/homepage.component";
import {TranslateModule} from "@ngx-translate/core";
import {SharedModule} from "@app/shared.module";
import {MarkdownModule} from "ngx-markdown";
import {TippageComponent} from "@app/pages/whistleblower/tippage/tippage.component";
import {
  WhistleblowerIdentityComponent
} from "@app/shared/partials/whistleblower-identity/whistleblower-identity.component";
import {FormsModule, ReactiveFormsModule} from "@angular/forms";
import {SubmissionComponent} from "@app/pages/whistleblower/submission/submission.component";
import {ContextSelectionComponent} from "@app/pages/whistleblower/context-selection/context-selection.component";
import {StepErrorComponent} from "@app/pages/whistleblower/step-error/step-error.component";
import {
  StepErrorEntryComponent
} from "@app/pages/whistleblower/step-error/template/step-error-entry/step-error-entry.component";
import {ReceiverSelectionComponent} from "@app/pages/whistleblower/receiver-selection/receiver-selection.component";
import {ReceiverCardComponent} from "@app/pages/whistleblower/receiver-card/receiver-card.component";
import {FormComponent} from "@app/pages/whistleblower/form/form.component";
import {FormFieldInputsComponent} from "@app/pages/whistleblower/form-field-inputs/form-field-inputs.component";
import {FormFieldInputComponent} from "@app/pages/whistleblower/form-field-input/form-field-input.component";
import {
  WhistleblowerIdentityFieldComponent
} from "./fields/whistleblower-identity-field/whistleblower-identity-field.component";
import {NgSelectModule} from "@ng-select/ng-select";
import {NgbInputDatepicker} from "@ng-bootstrap/ng-bootstrap";
import {ReceiptComponent} from "@app/pages/whistleblower/receipt/receipt.component";
import {
  TipAdditionalQuestionnaireFormComponent
} from "@app/shared/modals/tip-additional-questionnaire-form/tip-additional-questionnaire-form.component";


@NgModule({
  declarations: [
    HomepageComponent,
    TippageComponent,
    WhistleblowerIdentityComponent,
    SubmissionComponent,
    ContextSelectionComponent,
    StepErrorComponent,
    StepErrorEntryComponent,
    ReceiverSelectionComponent,
    ReceiverCardComponent,
    FormComponent,
    FormFieldInputsComponent,
    FormFieldInputComponent,
    WhistleblowerIdentityFieldComponent,
    ReceiptComponent,
    TipAdditionalQuestionnaireFormComponent,
  ],
  exports: [
    HomepageComponent,
    TippageComponent,
    SubmissionComponent,
    WhistleblowerIdentityFieldComponent,
    ReceiptComponent
  ],
  imports: [
    CommonModule,
    TranslateModule,
    SharedModule,
    MarkdownModule,
    ReactiveFormsModule,
    FormsModule,
    NgSelectModule,
    NgbInputDatepicker,
    NgOptimizedImage,
  ]
})
export class WhistleblowerModule {
}
