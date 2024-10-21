import { Component, OnInit, inject } from "@angular/core";
import {NgbActiveModal} from "@ng-bootstrap/ng-bootstrap";
import {PreferenceResolver} from "@app/shared/resolvers/preference.resolver";
import {AppDataService} from "@app/app-data.service";
import {preferenceResolverModel} from "@app/models/resolvers/preference-resolver-model";

import { FormsModule } from "@angular/forms";
import { TranslateModule } from "@ngx-translate/core";
import { TranslatorPipe } from "@app/shared/pipes/translate";

@Component({
    selector: "src-accept-agreement",
    templateUrl: "./accept-agreement.component.html",
    standalone: true,
    imports: [
    FormsModule,
    TranslateModule,
    TranslatorPipe
],
})
export class AcceptAgreementComponent implements OnInit {
  private activeModal = inject(NgbActiveModal);
  private preference = inject(PreferenceResolver);
  appDataService = inject(AppDataService);

  confirmFunction: () => void;
  preferenceData: preferenceResolverModel;
  accept: boolean = false;

  ngOnInit(): void {
    if (this.preference.dataModel) {
      this.preferenceData = this.preference.dataModel;
    }
  }

  confirm() {
    this.confirmFunction();
    return this.activeModal.close();
  }
}
