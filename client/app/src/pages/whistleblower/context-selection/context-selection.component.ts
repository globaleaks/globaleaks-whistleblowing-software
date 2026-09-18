import {Component, inject, input, output} from "@angular/core";
import {AppDataService} from "@app/app-data.service";
import {Context} from "@app/models/app/public-model";
import {UtilsService} from "@app/shared/services/utils.service";
import {MarkdownComponent} from "ngx-markdown";
import {StripHtmlPipe} from "@app/shared/pipes/strip-html.pipe";
import {OrderByPipe} from "@app/shared/pipes/order-by.pipe";

@Component({
    selector: "src-context-selection",
    templateUrl: "./context-selection.component.html",
    standalone: true,
    imports: [MarkdownComponent, StripHtmlPipe, OrderByPipe]
})
export class ContextSelectionComponent {
  protected appDataService = inject(AppDataService);
  protected utilsService = inject(UtilsService);

  readonly selectable_contexts = input.required<Context[]>();
  readonly contextsOrderPredicate = input.required<string>();
  readonly selectContext = output<any>();
}
