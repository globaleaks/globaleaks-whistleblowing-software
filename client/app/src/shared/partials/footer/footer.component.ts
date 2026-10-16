import {Component, inject} from "@angular/core";
import {AppDataService} from "@app/app-data.service";

import {MarkdownComponent} from "ngx-markdown";
import {TranslatePipe} from "@ngx-translate/core";
import {StripHtmlPipe} from "@app/shared/pipes/strip-html.pipe";

@Component({
    selector: "app-footer",
    templateUrl: "./footer.component.html",
    standalone: true,
    imports: [MarkdownComponent, TranslatePipe, StripHtmlPipe]
})
export class FooterComponent {
  protected appDataService = inject(AppDataService);
}
