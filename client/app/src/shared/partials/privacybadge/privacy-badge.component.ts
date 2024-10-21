import {Component, inject} from "@angular/core";
import {AppDataService} from "@app/app-data.service";
import {UtilsService} from "@app/shared/services/utils.service";
import {MarkdownComponent} from "ngx-markdown";
import {TranslateModule} from "@ngx-translate/core";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {StripHtmlPipe} from "@app/shared/pipes/strip-html.pipe";
import {NgbTooltipModule} from '@ng-bootstrap/ng-bootstrap';


@Component({
    selector: "src-privacybadge",
    templateUrl: "./privacy-badge.component.html",
    standalone: true,
    imports: [MarkdownComponent, NgbTooltipModule, TranslateModule, TranslatorPipe, StripHtmlPipe]
})
export class PrivacyBadgeComponent {
  protected appDataService = inject(AppDataService);
  protected utilsService = inject(UtilsService);

  public markdown: string;

  constructor() {
    const appDataService = this.appDataService;

    this.markdown = appDataService.public.node.custom_privacy_badge_text;
  }

}
