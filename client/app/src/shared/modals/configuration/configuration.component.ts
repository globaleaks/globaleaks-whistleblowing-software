import {Component, inject} from "@angular/core";
import {NgbActiveModal} from "@ng-bootstrap/ng-bootstrap";
import {TranslateModule} from "@ngx-translate/core";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {NetworkResolver} from "@app/shared/resolvers/network.resolver";
import {NotificationsResolver} from "@app/shared/resolvers/notifications.resolver";
import {UtilsService} from "@app/shared/services/utils.service";
import {SelectionEditorComponent, SelectionEntry} from "@app/shared/components/selection-editor/selection-editor.component";

@Component({
  selector: "src-configuration",
  templateUrl: "./configuration.component.html",
  standalone: true,
  imports: [SelectionEditorComponent, TranslateModule]
})
export class ConfigurationComponent {
  private readonly activeModal = inject(NgbActiveModal);
  private readonly utilsService = inject(UtilsService);
  // A value given up here changes what the fields behind show: the node is read again on the way
  // out, and only when something was actually given up
  private gaveUp = false;
  protected readonly nodeResolver = inject(NodeResolver);
  private readonly networkResolver = inject(NetworkResolver);
  private readonly notificationsResolver = inject(NotificationsResolver);

  // A profile names here the variables it leaves free to the sites naming it; a site reads here
  // the variables it holds of its own, and gives up the ones it no longer wants
  get isProfile(): boolean {
    return this.nodeResolver.dataModel.is_profile;
  }

  get namesProfile(): boolean {
    return !!this.nodeResolver.dataModel.writable_keys;
  }

  private entries(keys: string[]): SelectionEntry[] {
    return (keys || []).map(key => ({id: key, label: key}));
  }

  get selected(): SelectionEntry[] {
    return this.entries(this.isProfile ? this.nodeResolver.dataModel.unlocked_keys
                                       : this.nodeResolver.dataModel.held_keys);
  }

  get options(): SelectionEntry[] {
    if (!this.isProfile) {
      return [];
    }

    const unlocked = this.nodeResolver.dataModel.unlocked_keys || [];

    return this.entries((this.nodeResolver.dataModel.unlockable_keys || [])
      .filter(key => !unlocked.includes(key)));
  }

  add(key: string): void {
    this.utilsService.runAdminOperation("unlock_key", {value: key}, false)
      .subscribe(() => {
        this.nodeResolver.patch({unlocked_keys: [...this.nodeResolver.dataModel.unlocked_keys, key].sort()});
      });
  }

  remove(key: string): void {
    const operation = this.isProfile ? "lock_key" : "reset_key";

    this.utilsService.runAdminOperation(operation, {value: key}, false)
      .subscribe(() => {
        if (this.isProfile) {
          this.nodeResolver.patch({
            unlocked_keys: this.nodeResolver.dataModel.unlocked_keys.filter(entry => entry !== key)
          });
        } else {
          this.nodeResolver.patch({
            held_keys: this.nodeResolver.dataModel.held_keys.filter(entry => entry !== key)
          });
          this.gaveUp = true;
        }
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
