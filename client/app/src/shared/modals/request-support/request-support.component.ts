import {Component, OnInit, inject} from "@angular/core";
import {NgbActiveModal} from "@ng-bootstrap/ng-bootstrap";
import {UtilsService} from "@app/shared/services/utils.service";
import {PreferenceResolver} from "@app/shared/resolvers/preference.resolver";
import {Constants} from "@app/shared/constants/constants";
import {FormsModule} from "@angular/forms";

import {TranslateModule} from "@ngx-translate/core";
import {TranslatorPipe} from "@app/shared/pipes/translate";

@Component({
    selector: "src-request-support",
    templateUrl: "./request-support.component.html",
    standalone: true,
    imports: [FormsModule, TranslateModule, TranslatorPipe]
})
export class RequestSupportComponent implements OnInit {
  protected activeModal = inject(NgbActiveModal);
  protected utilsService = inject(UtilsService);
  private preferenceResolver = inject(PreferenceResolver);

  protected readonly Constants = Constants;
  sent = false;
  arg: { mail_address: string, text: string } = {mail_address: "", text: ""};

  ngOnInit(): void {
    this.arg.mail_address = this.preferenceResolver.dataModel.mail_address;
  }
}