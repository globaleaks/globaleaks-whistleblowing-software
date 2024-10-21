import { Component, EventEmitter, Input, Output, inject } from "@angular/core";
import {AppDataService} from "@app/app-data.service";
import {Context} from "@app/models/app/public-model";
import {UtilsService} from "@app/shared/services/utils.service";
import { NgOptimizedImage } from "@angular/common";
import { MarkdownComponent } from "ngx-markdown";
import { StripHtmlPipe } from "@app/shared/pipes/strip-html.pipe";
import { OrderByPipe } from "@app/shared/pipes/order-by.pipe";

@Component({
    selector: "src-context-selection",
    templateUrl: "./context-selection.component.html",
    standalone: true,
    imports: [MarkdownComponent, NgOptimizedImage, StripHtmlPipe, OrderByPipe]
})
export class ContextSelectionComponent {
  protected appDataService = inject(AppDataService);
  protected utilsService = inject(UtilsService);


  @Input() selectable_contexts: Context[];
  @Input() contextsOrderPredicate: string;
  @Output() selectContext: EventEmitter<any> = new EventEmitter();
}
