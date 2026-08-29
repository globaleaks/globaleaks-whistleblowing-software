import {NgClass, NgTemplateOutlet} from "@angular/common";
import {Component, Input, inject} from "@angular/core";
import {FormsModule} from "@angular/forms";
import {DateRangeSelectorComponent} from "@app/shared/components/date-selector/date-selector.component";
import {TableFilterOption, TableState} from "@app/shared/components/table/table-state";
import {TranslateService} from "@ngx-translate/core";
import {IDropdownSettings, NgMultiSelectDropDownModule} from "ng-multiselect-dropdown";

/**
 * Header of a sortable and filterable column.
 *
 * It is applied to the th itself so that the table markup stays the browser
 * one: <th appTableHeader [state]="table" [label]="'Status' | translate"
 *          sortBy="status" filter="status" [options]="statusOptions">
 */
@Component({
  selector: "th[appTableHeader]",
  templateUrl: "./table-header.component.html",
  standalone: true,
  imports: [DateRangeSelectorComponent, FormsModule, NgClass, NgMultiSelectDropDownModule, NgTemplateOutlet]
})
export class TableHeaderComponent {
  private translateService = inject(TranslateService);

  @Input({required: true}) state!: TableState<any>;
  @Input() label = "";
  /** Icon shown before the label, e.g. "fa-star" */
  @Input() icon = "";
  /** The label is only read by the screen readers: the icon names the column */
  @Input() labelHidden = false;
  /** Property the column sorts on; the column is not sortable without it */
  @Input() sortBy = "";
  /** Key of the filter declared on the state; the column has no filter without it */
  @Input() filter = "";
  @Input() options: TableFilterOption[] = [];

  readonly dropdownSettings: IDropdownSettings = {
    idField: "id",
    textField: "label",
    itemsShowLimit: 3,
    allowSearchFilter: true,
    selectAllText: this.translateService.instant("Select all"),
    unSelectAllText: this.translateService.instant("Deselect all"),
    searchPlaceholderText: this.translateService.instant("Search")
  };

  get filterType(): string {
    return this.filter && this.state.filters[this.filter] ? this.state.filters[this.filter].type : "";
  }
}
