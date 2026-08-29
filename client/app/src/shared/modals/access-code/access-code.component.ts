import {Component, Input, OnInit, inject} from "@angular/core";
import {NgbActiveModal, NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {UtilsService} from "@app/shared/services/utils.service";
import {TranslateModule} from "@ngx-translate/core";

@Component({
    selector: "src-access-code",
    templateUrl: "./access-code.component.html",
    standalone: true,
    imports: [NgbTooltipModule, TranslateModule]
})
export class AccessCodeComponent implements OnInit {
  private readonly activeModal = inject(NgbActiveModal);
  protected utilsService = inject(UtilsService);

  @Input() code: string;

  formattedCode = "";

  ngOnInit() {
    // The code is presented as the receipt is presented to the whistleblower,
    // in groups of four digits
    this.formattedCode = (this.code.match(/.{1,4}/g) || []).join(" ");
  }

  dismiss() {
    this.activeModal.dismiss();
  }
}
