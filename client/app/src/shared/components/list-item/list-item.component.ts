import {ChangeDetectionStrategy, Component, contentChild, input, model, output, TemplateRef} from "@angular/core";
import {NgTemplateOutlet} from "@angular/common";
import {NgbTooltip} from "@ng-bootstrap/ng-bootstrap";
import {TranslatePipe} from "@ngx-translate/core";

/**
 * Expandable item of an administrative list.
 *
 * The header shows the projected [title] on the left and the action buttons
 * on the right: Save while editing, the projected [leading] buttons, the
 * projected [actions], Delete when the item is deletable, the projected
 * [reorder] arrows and, at the far right, the button that opens and closes
 * the item: there is no Cancel, since closing is all it did. A readOnly item
 * is opened and read but not written: it carries no Save or Delete, and what
 * it displays is left to the editor it holds.
 * The editor declared as <ng-template #body> is instantiated only while the
 * item is being edited, so the form controls of the closed items never exist.
 *
 * The buttons carry no id, since the item is repeated in a list: tests reach
 * them through the row container and the data-action attribute.
 */
@Component({
  selector: "src-list-item",
  standalone: true,
  imports: [NgTemplateOutlet, NgbTooltip, TranslatePipe],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="config-item">
      <div class="editorHeader row">
        <span class="col-md-{{ titleColumns() }}" (click)="toggle()" (keydown.enter)="toggle()" tabindex="0" role="button" [attr.aria-expanded]="editing()">
          <ng-content select="[title]"></ng-content>
        </span>
        <span class="col-md-{{ 12 - titleColumns() }} clearfix">
          <span class="float-end">
            @if (editing() && !readOnly()) {
              <button type="button" class="btn btn-sm btn-primary" data-action="save" [disabled]="saveDisabled()" (click)="onSave()">
                <span>{{ 'Save' | translate }}</span>
              </button>
            }
            <ng-content select="[leading]"></ng-content>
            <ng-content select="[actions]"></ng-content>
            @if (canDelete()) {
              <button type="button" class="btn btn-sm btn-danger" data-action="delete" (click)="deleted.emit()">
                <span>{{ 'Delete' | translate }}</span>
              </button>
            }
            <ng-content select="[reorder]"></ng-content>
            @if (canEdit() || readOnly() || editing()) {
              <button type="button" class="btn btn-sm btn-outline-secondary" data-action="edit" [attr.aria-expanded]="editing()" [attr.aria-label]="(editing() ? 'Close' : 'Open') | translate" ngbTooltip="{{ (editing() ? 'Close' : 'Open') | translate }}" (click)="toggle()">
                @if (editing()) {
                  <i class="fas fa-chevron-up" aria-hidden="true"></i>
                } @else {
                  <i class="fas fa-chevron-down" aria-hidden="true"></i>
                }
              </button>
            }
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

  /** The item is opened and read, and none of its buttons is offered */
  readonly readOnly = input(false);
  readonly saveDisabled = input(false);

  /** Width of the title column; the actions take the remaining ones */
  readonly titleColumns = input(7);

  readonly save = output<void>();
  readonly deleted = output<void>();

  readonly body = contentChild<TemplateRef<unknown>>("body");

  toggle(): void {
    if (this.canEdit() || this.readOnly() || this.editing()) {
      this.editing.set(!this.editing());
    }
  }

  protected onSave(): void {
    this.save.emit();
    this.editing.set(false);
  }
}
