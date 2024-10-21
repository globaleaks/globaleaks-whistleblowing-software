import {Component, Input, OnInit, inject} from "@angular/core";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {LoginDataRef} from "@app/pages/auth/login/model/login-model";
import {NgForm, FormsModule} from "@angular/forms";
import {AppDataService} from "@app/app-data.service";

import {NgSelectComponent, NgOptionComponent} from "@ng-select/ng-select";
import {TranslateModule} from "@ngx-translate/core";
import {TranslatorPipe} from "@app/shared/pipes/translate";

@Component({
    selector: "app-simple-login",
    templateUrl: "./simple-login.component.html",
    standalone: true,
    imports: [
    FormsModule,
    NgSelectComponent,
    NgOptionComponent,
    TranslateModule,
    TranslatorPipe
],
})
export class SimpleLoginComponent implements OnInit {
  protected authentication = inject(AuthenticationService);
  protected appDataService = inject(AppDataService);


  @Input() loginData: LoginDataRef;
  @Input() loginValidator: NgForm;

  public ngOnInit(): void {

  }
}
