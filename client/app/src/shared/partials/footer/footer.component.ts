import {Component, inject} from "@angular/core";
import {AppDataService} from "@app/app-data.service";

import {MarkdownComponent} from "ngx-markdown";
import {TranslateModule} from "@ngx-translate/core";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {StripHtmlPipe} from "@app/shared/pipes/strip-html.pipe";

@Component({
    selector: "app-footer",
    templateUrl: "./footer.component.html",
    standalone: true,
    imports: [MarkdownComponent, TranslateModule, TranslatorPipe, StripHtmlPipe]
})
export class FooterComponent {
  protected appDataService = inject(AppDataService);
}
