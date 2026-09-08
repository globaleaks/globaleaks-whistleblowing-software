import {Component, inject} from "@angular/core";
import {NgbActiveModal, NgbModal} from "@ng-bootstrap/ng-bootstrap";
import {TranslateModule} from "@ngx-translate/core";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {NetworkResolver} from "@app/shared/resolvers/network.resolver";
import {NotificationsResolver} from "@app/shared/resolvers/notifications.resolver";
import {UtilsService} from "@app/shared/services/utils.service";
import {ConfirmationComponent} from "@app/shared/modals/confirmation/confirmation.component";
import {SelectionEditorComponent, SelectionEntry} from "@app/shared/components/selection-editor/selection-editor.component";

/**
 * What a tenant decides of its configuration, read whole instead of walked field by field.
 *
 * Two questions, and a panel each. What the tenant holds of its own is the first, and it is asked
 * of a profile and of a site alike: the answer is a list of variables, each of which can be given
 * back to the value it is handed. What the tenant leaves free to the sites naming it is the
 * second, and only a profile has it: there a variable is added to be left free and removed to be
 * kept, which is the lock closing again.
 *
 * The same two decisions are taken beside each field, by the two commands of the strip; here they
 * are read together, which is the only way to see what a profile is doing without walking every
 * page it has.
 */
@Component({
  selector: "src-configuration",
  templateUrl: "./configuration.component.html",
  standalone: true,
  imports: [SelectionEditorComponent, TranslateModule]
})
export class ConfigurationComponent {
  private readonly activeModal = inject(NgbActiveModal);
  private readonly utilsService = inject(UtilsService);
  private readonly modalService = inject(NgbModal);
  // A value given up here changes what the fields behind show: the node is read again on the way
  // out, and only when something was actually given up
  private gaveUp = false;
  protected readonly nodeResolver = inject(NodeResolver);
  private readonly networkResolver = inject(NetworkResolver);
  private readonly notificationsResolver = inject(NotificationsResolver);

  get isProfile(): boolean {
    return this.nodeResolver.dataModel.is_profile;
  }

  // What this tenant configured of its own, and what a profile leaves to the sites naming it
  readonly heldLabel = "Custom";

  readonly customizableLabel = "Customizable";

  private entries(keys: string[]): SelectionEntry[] {
    return (keys || []).map(key => ({id: key, label: key}));
  }

  get held(): SelectionEntry[] {
    return this.entries(this.nodeResolver.dataModel.held_keys);
  }

  get customizable(): SelectionEntry[] {
    return this.entries(this.nodeResolver.dataModel.customizable_keys);
  }

  // What is left to leave customizable: the whole of what the application allows a profile to
  // decide of, less what this profile has already left
  get lockable(): SelectionEntry[] {
    const customizable = this.nodeResolver.dataModel.customizable_keys || [];

    return this.entries((this.nodeResolver.dataModel.unlockable_keys || [])
      .filter(key => !customizable.includes(key)));
  }

  unlock(key: string): void {
    this.utilsService.runAdminOperation("unlock_key", {value: key}, false)
      .subscribe(() => {
        this.nodeResolver.patch({customizable_keys: [...this.nodeResolver.dataModel.customizable_keys, key].sort()});
      });
  }

  // Taking a variable back drops the values the sites naming the profile configured of it, and is
  // asked first. Declining closes the question alone and leaves this window open.
  lock(key: string): void {
    const modalRef = this.modalService.open(ConfirmationComponent, {backdrop: "static", keyboard: false, ariaLabelledBy: "modal-title"});
    modalRef.componentInstance.message = "Please note that all the associated data will be permanently deleted.";
    modalRef.componentInstance.cancel = () => modalRef.dismiss();
    modalRef.componentInstance.confirmFunction = () => {
      this.utilsService.runAdminOperation("lock_key", {value: key}, false)
        .subscribe(() => {
          this.nodeResolver.patch({
            customizable_keys: this.nodeResolver.dataModel.customizable_keys.filter(entry => entry !== key)
          });
        });
    };
  }

  giveUp(key: string): void {
    this.utilsService.runAdminOperation("reset_key", {value: key}, false)
      .subscribe(() => {
        this.nodeResolver.patch({
          held_keys: this.nodeResolver.dataModel.held_keys.filter(entry => entry !== key)
        });
        this.gaveUp = true;
      });
  }

  close(): void {
    this.activeModal.close();

    if (this.gaveUp) {
      this.nodeResolver.reload();
      this.networkResolver.reload();
      this.notificationsResolver.reload();
    }
  }
}
