import {Component, inject, input, output} from "@angular/core";
import {SubmissionService} from "@app/services/helper/submission.service";
import {UtilsService} from "@app/shared/services/utils.service";
import {NgClass} from "@angular/common";
import {ReceiverCardComponent} from "../receiver-card/receiver-card.component";
import {TranslateModule} from "@ngx-translate/core";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {FilterPipe} from "@app/shared/pipes/filter.pipe";
import {OrderByPipe} from "@app/shared/pipes/order-by.pipe";

@Component({
    selector: "src-receiver-selection",
    templateUrl: "./receiver-selection.component.html",
    standalone: true,
    imports: [NgClass, ReceiverCardComponent, TranslateModule, TranslatorPipe, FilterPipe, OrderByPipe]
})
export class ReceiverSelectionComponent {
  protected utilsService = inject(UtilsService);

  readonly show_steps_navigation_bar = input<boolean>();
  readonly submission = input.required<SubmissionService>();
  readonly receiversOrderPredicate = input.required<string>();
  readonly switchSelection = output<any>();
}
