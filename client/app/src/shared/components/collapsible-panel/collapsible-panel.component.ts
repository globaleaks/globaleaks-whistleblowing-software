import {Component, input, output} from "@angular/core";
import {NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {TranslatePipe} from "@ngx-translate/core";

/**
 * The header of a panel of the report opening on its own body.
 *
 * It is applied to the card itself so that the caller keeps its identifier
 * and its classes:
 *
 *   <div srcCollapsiblePanel id="TipCommentsBox" class="card"
 *        [collapsed]="collapsed" [label]="'Comments' | translate"
 *        (panelToggle)="toggleCollapse()">
 *     @if (!collapsed) { <div class="card-body">…</div> }
 *   </div>
 *
 * The header is operated with the keyboard as well and tells whether the
 * panel is open; a title richer than a label is projected on [panelTitle].
 */
@Component({
    // An attribute and not an element, so that the card keeps the identifier and the classes of its caller
    // eslint-disable-next-line @angular-eslint/component-selector
    selector: "div[srcCollapsiblePanel]",
    templateUrl: "./collapsible-panel.component.html",
    standalone: true,
    imports: [NgbTooltipModule, TranslatePipe]
})
export class CollapsiblePanelComponent {
  readonly collapsed = input(false);
  readonly label = input("");
  /** Some panels are opened from their own body and carry no chevron */
  readonly chevron = input(true);
  // Not "toggle", the name of an event of the DOM that would be heard as well
  readonly panelToggle = output<void>();
}
