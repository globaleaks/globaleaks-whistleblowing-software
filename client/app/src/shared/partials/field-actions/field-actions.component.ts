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
 * Two commands, always in the same place and always present: the colour says whether they do
 * anything, so that a page can be read at a glance instead of hunted through. A profile carries
 * both — the lock, by which it keeps a variable for itself or leaves it to the sites naming it,
 * and the giving up of a value of its own; a site carries the giving up alone, because it has
 * nobody to leave anything to.
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

  // The lock is a matter for a profile alone, and only on the variables the application allows
  // it to leave free
  get lockShown(): boolean {
    return this.nodeResolver.dataModel.is_profile &&
      (this.nodeResolver.dataModel.unlockable_keys || []).includes(this.key);
  }

  get locked(): boolean {
    return !(this.nodeResolver.dataModel.unlocked_keys || []).includes(this.key);
  }

  // There is something to give up only while the tenant holds a value of its own: where there is
  // not, the command is not there either. The lock, which keeps its place either way, sits to its
  // right, so that it does not move as the other comes and goes.
  get held(): boolean {
    return (this.nodeResolver.dataModel.held_keys || []).includes(this.key);
  }

  toggleLock(): void {
    const locked = this.locked;

    this.utilsService.runAdminOperation(locked ? "unlock_key" : "lock_key", {value: this.key}, false)
      .subscribe(() => {
        const keys = this.nodeResolver.dataModel.unlocked_keys.filter(key => key !== this.key);

        if (locked) {
          keys.push(this.key);
        }

        this.nodeResolver.patch({unlocked_keys: keys.sort()});
      });
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
