import {Component, inject} from "@angular/core";
import {NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {TranslateModule} from "@ngx-translate/core";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {NetworkResolver} from "@app/shared/resolvers/network.resolver";
import {NotificationsResolver} from "@app/shared/resolvers/notifications.resolver";
import {UtilsService} from "@app/shared/services/utils.service";

/**
 * Who decides the value of a field, said at the end of the line of its label.
 *
 * One command, the giving up of a value of one's own, which a profile and a site carry alike.
 * Which variables a profile leaves free to the sites naming it is said in one place, among the
 * settings, and not field by field: said beside a field it would name a lock that, on the page
 * where it is pressed, locks nothing.
 */
@Component({
  selector: "src-field-actions",
  templateUrl: "./field-actions.component.html",
  standalone: true,
  // The class goes on the element of the component and not on a span inside it: between the
  // label and that span there would be the element itself, and a rule written with the child
  // combinator would never match it
  host: {"class": "field-actions"},
  imports: [NgbTooltipModule, TranslateModule]
})
export class FieldActionsComponent {
  private readonly nodeResolver = inject(NodeResolver);
  private readonly networkResolver = inject(NetworkResolver);
  private readonly notificationsResolver = inject(NotificationsResolver);
  private readonly utilsService = inject(UtilsService);

  key = "";

  // There is something to give up only while the tenant holds a value of its own: where there is
  // not, the command is not there either.
  get held(): boolean {
    return (this.nodeResolver.dataModel.held_keys || []).includes(this.key);
  }

  // The panels that configure a site are read again on the spot: the value the profile hands
  // reaches the field without a navigation. The variable belongs to one of the three, and which
  // one is not worth asking: rereading is cheap and giving up a value is rare.
  reset(): void {
    if (!this.held) {
      return;
    }

    this.utilsService.runAdminOperation("reset_key", {value: this.key}, false)
      .subscribe(() => {
        this.nodeResolver.reload();
        this.networkResolver.reload();
        this.notificationsResolver.reload();
      });
  }
}
