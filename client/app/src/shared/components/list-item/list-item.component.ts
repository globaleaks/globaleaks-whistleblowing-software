import {ChangeDetectionStrategy, Component, contentChild, input, model, output, TemplateRef} from "@angular/core";
import {NgTemplateOutlet} from "@angular/common";
import {TranslatePipe} from "@ngx-translate/core";

/**
 * Expandable item of an administrative list.
 *
 * The header shows the projected [title] on the left and the action buttons
 * on the right: Edit, Save and Cancel follow the editing state, Delete is
 * shown when the item is deletable, and any projected [actions] come last.
 * The editor declared as <ng-template #body> is instantiated only while the
 * item is being edited, so the form controls of the closed items never exist.
 *
 * The buttons carry no id, since the item is repeated in a list: tests reach
 * them through the row container and the data-action attribute.
 */
@Component({
  selector: "src-list-item",
  standalone: true,
  imports: [NgTemplateOutlet, TranslatePipe],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="config-item">
      <div class="editorHeader row">
        <span class="col-md-{{ titleColumns() }}" (click)="toggle()" (keydown.enter)="toggle()" tabindex="0" role="button" [attr.aria-expanded]="editing()">
          <ng-content select="[title]"></ng-content>
        </span>
        <span class="col-md-{{ 12 - titleColumns() }} clearfix">
          <span class="float-end">
            @if (canEdit() && !editing()) {
              <button type="button" class="btn btn-sm btn-outline-secondary" data-action="edit" (click)="toggle()">
                <span>{{ 'Edit' | translate }}</span>
              </button>
            }
            @if (editing()) {
              <button type="button" class="btn btn-sm btn-primary" data-action="save" [disabled]="saveDisabled()" (click)="onSave()">
                <span>{{ 'Save' | translate }}</span>
              </button>
              <button type="button" class="btn btn-sm btn-outline-secondary" data-action="cancel" (click)="onCancel()">
                <span>{{ 'Cancel' | translate }}</span>
              </button>
            }
            @if (canDelete()) {
              <button type="button" class="btn btn-sm btn-danger" data-action="delete" (click)="deleted.emit()">
                <span>{{ 'Delete' | translate }}</span>
              </button>
            }
            <ng-content select="[actions]"></ng-content>
          </span>
        </span>
      </div>
      @if (editing() && body(); as body) {
        <div>
          <hr />
          <ng-container [ngTemplateOutlet]="body"></ng-container>
        </div>
      }
    </div>
  `
})
export class ListItemComponent {
  readonly editing = model(false);
  readonly canEdit = input(true);
  readonly canDelete = input(true);
  readonly saveDisabled = input(false);

  /** Width of the title column; the actions take the remaining ones */
  readonly titleColumns = input(7);

  readonly save = output<void>();
  readonly cancelled = output<void>();
  readonly deleted = output<void>();

  readonly body = contentChild<TemplateRef<unknown>>("body");

  toggle(): void {
    if (this.canEdit() || this.editing()) {
      this.editing.set(!this.editing());
    }
  }

  protected onSave(): void {
    this.save.emit();
    this.editing.set(false);
  }

  protected onCancel(): void {
    this.cancelled.emit();
    this.editing.set(false);
  }
}
