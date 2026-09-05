import {Component, OnChanges, input, output} from "@angular/core";
import {FormsModule} from "@angular/forms";
import {NgSelectComponent, NgOptionTemplateDirective} from "@ng-select/ng-select";
import {NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {TranslateModule} from "@ngx-translate/core";

export interface SelectionEntry {
  id: string;
  label: string;
}

/**
 * Editor of a selection of entries with a default: a label and an Add button
 * revealing the selector of the entries not yet held, above the list of the
 * held ones, where the check mark sets the default on one entry at a time
 * and the entry holding it cannot be removed.
 */
@Component({
    selector: "src-selection-editor",
    templateUrl: "./selection-editor.component.html",
    standalone: true,
    imports: [FormsModule, NgSelectComponent, NgOptionTemplateDirective, NgbTooltipModule, TranslateModule]
})
export class SelectionEditorComponent implements OnChanges {
  readonly label = input("");
  // The label names the group and the selector for the assistive technologies
  // in any case: hiding it only takes it off the screen, for the callers whose
  // surroundings (the title of a tab, a heading) already say it
  readonly hideLabel = input(false);
  readonly required = input(false);

  // Stable hooks for the tests, e.g. add-language-btn / LanguageAdder
  readonly addButtonClass = input("");
  readonly adderId = input("");

  readonly options = input<SelectionEntry[]>([]);
  readonly selected = input<SelectionEntry[]>([]);
  // The entry that cannot be removed: its remove control is never shown. With
  // selectableDefault it is also the one holding the default check mark
  readonly defaultId = input("");

  // When false the default marker (the check mark electing an entry as the
  // default) is hidden and the list offers only add and remove; the defaultId
  // entry, if any, still cannot be removed
  readonly selectableDefault = input(true);

  // How the election is named to the readers: 'Default' where the elected entry is what happens by
  // itself
  readonly defaultLabel = input("Default");
  readonly defaultTooltip = input("Use as default");

  // When true the election can be cleared from its check mark, emitting an empty defaultPicked
  readonly clearableDefault = input(false);

  readonly entryAdded = output<string>();
  readonly entryRemoved = output<{index: number, id: string}>();
  readonly defaultPicked = output<string>();

  // Each instance labels its own group: the ids must not collide when many
  // editors share a page
  private static instances = 0;
  labelId = `selection-editor-label-${SelectionEditorComponent.instances++}`;

  showSelect = false;
  selection: string | null = null;

  // ng-select rebuilds the option DOM whenever [items] changes reference,
  // killing the click in flight when the callers recompute the options on
  // every change-detection tick: hold the reference until the content changes.
  stableOptions: SelectionEntry[] = [];

  ngOnChanges() {
    const options = this.options();

    if (options.length !== this.stableOptions.length ||
        options.some((option, i) => option.id !== this.stableOptions[i]?.id || option.label !== this.stableOptions[i]?.label)) {
      this.stableOptions = options;
    }
  }

  toggleSelect() {
    this.showSelect = !this.showSelect;
  }

  pick(id: string | null) {
    if (id) {
      this.entryAdded.emit(id);
    }

    this.selection = null;
    this.showSelect = false;
  }
}
