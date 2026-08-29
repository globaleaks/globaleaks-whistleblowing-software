import {Component, input, output} from "@angular/core";
import {TranslateModule} from "@ngx-translate/core";

/**
 * A card of a list opening on its own body.
 *
 * Unlike src-list-item, which owns the Edit, Save, Cancel and Delete buttons
 * of the administrative lists, this card only opens and closes: the caller
 * projects the title, every action of the header and the body it shows while
 * open. The title and the chevron are buttons, so that the card is reached
 * and opened with the keyboard as well.
 */
@Component({
    selector: "src-collapsible-card",
    templateUrl: "./collapsible-card.component.html",
    standalone: true,
    imports: [TranslateModule]
})
export class CollapsibleCardComponent {
  readonly expanded = input(false);
  /** Classes of the box; empty when the caller already provides its own */
  readonly cardClass = input("config-item");
  /** Width of the title, on the twelve columns of the header */
  readonly titleColumns = input(7);
  /** Some cards open only through their own actions and carry no chevron */
  readonly chevron = input(true);
  readonly toggle = output<void>();

  get actionsColumns(): number {
    return 12 - this.titleColumns();
  }
}
