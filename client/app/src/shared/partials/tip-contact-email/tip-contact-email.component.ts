import {Component, inject, OnInit} from "@angular/core";
import {FormsModule} from "@angular/forms";
import {WbtipService} from "@app/services/helper/wbtip.service";
import {HttpService} from "@app/shared/services/http.service";
import {UtilsService} from "@app/shared/services/utils.service";
import {TranslateModule} from "@ngx-translate/core";
import {TranslatorPipe} from "@app/shared/pipes/translate";

@Component({
    selector: "src-tip-contact-email",
    templateUrl: "./tip-contact-email.component.html",
    standalone: true,
    imports: [FormsModule, TranslateModule, TranslatorPipe]
})
export class TipContactEmailComponent implements OnInit {
  protected wbTipService = inject(WbtipService);
  private httpService = inject(HttpService);
  protected utilsService = inject(UtilsService);

  email = '';
  collapsed = false;

  ngOnInit() {
    this.email = this.wbTipService.tip?.data?.contact_email || '';
  }

  toggleCollapse() {
    this.collapsed = !this.collapsed;
  }

  updateEmail() {
    this.httpService.whistleBlowerContactEmailUpdate({contact_email: this.email}).subscribe(() => {
      this.wbTipService.tip.data.contact_email = this.email;
    });
  }
}
