import {NgModule} from "@angular/core";
import {MarkdownModule} from "ngx-markdown";
import {CommonModule} from "@angular/common";
import {SignupComponent} from "@app/pages/signup/signup/signup.component";
import {TranslateModule} from "@ngx-translate/core";
import {SignupdefaultComponent} from "@app/pages/signup/templates/signupdefault/signupdefault.component";
import {SharedModule} from "@app/shared.module";
import {FormsModule, ReactiveFormsModule} from "@angular/forms";
import {NgSelectModule} from "@ng-select/ng-select";
import {TosComponent} from "@app/pages/signup/templates/tos/tos.component";
import {WbpaComponent} from "@app/pages/signup/templates/wbpa/wbpa.component";
import {ActivationComponent} from "@app/pages/signup/templates/activation/activation.component";


@NgModule({
  declarations: [
    SignupComponent,
    SignupdefaultComponent,
    TosComponent,
    WbpaComponent,
    ActivationComponent
  ],
  imports: [
    CommonModule,
    MarkdownModule,
    TranslateModule,
    FormsModule,
    ReactiveFormsModule,
    NgSelectModule,
    SharedModule
  ]
})
export class SignupModule {
}
