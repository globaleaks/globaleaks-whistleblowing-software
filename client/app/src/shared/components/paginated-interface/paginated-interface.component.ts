import {AfterViewInit, Component, contentChild, inject, input, model, OnChanges, SimpleChanges, TemplateRef} from '@angular/core';
import {NgTemplateOutlet} from '@angular/common';
import {FormsModule} from '@angular/forms';
import {UtilsService} from "@app/shared/services/utils.service";
import {SearchInputComponent} from '@app/shared/components/search/search.component';
import {PaginationComponent} from '@app/shared/components/pagination/pagination.component';

@Component({
  selector: 'app-paginated-interface',
  templateUrl: './paginated-interface.component.html',
  imports: [FormsModule, NgTemplateOutlet, PaginationComponent, SearchInputComponent],
})
export class PaginatedInterfaceComponent<T> implements AfterViewInit, OnChanges {
  readonly mode = input<'table' | 'simple'>('simple');
  readonly items = input<T[]>([]);
  readonly filterField = input('');
  readonly itemsPerPage = input(20);

  /** Optional: filter by key-value pairs */
  readonly filter = input<Record<string, any>>();

  /** Optional boolean filter, offered next to the search as a checkbox */
  readonly filterOptLabel = input('');
  readonly filterOptEnabled = model(false);
  readonly filterOptFn = input<(item: T) => boolean>();

  /** Optional: order items by field and direction */
  readonly orderBy = input<keyof T>();
  readonly orderDesc = input(false);

  /** Optional: the identifier of the item the interface must open on */
  readonly focusItemId = input('');

  /** Templates (auto-detected if mode not set) */
  readonly header = contentChild<TemplateRef<any>>('header');
  readonly content = contentChild<TemplateRef<any>>('content');

  /** Optional collection actions (e.g. Add, Import) shown on the left of the search input */
  readonly toolbar = contentChild<TemplateRef<unknown>>('toolbar');

  /** Optional creation form shown between the toolbar and the list */
  readonly addForm = contentChild<TemplateRef<unknown>>('addForm');

  searchText = '';
  currentPage = 1;
  filteredItems: T[] = [];
  paginatedItems: T[] = [];

  // The items surviving the structural filter alone: the search is offered
  // only when it has something to narrow down
  scopedCount = 0;

  // The item the interface has already been positioned on: the position is
  // taken once, so that the pages turned afterwards are the ones of the reader
  private focusedItemId = '';

  private utilsService = inject(UtilsService);

  ngAfterViewInit(): void {
    this.update();
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['items'] || changes['filter'] || changes['orderBy'] || changes['orderDesc'] || changes['focusItemId']) {
      // A shorter list may no longer hold the page in view
      this.currentPage = 1;
      this.update();
    }
  }

  update(): void {
    this.filteredItems = [...this.items()];

    // Apply optional filter object
    if (this.filter()) {
      this.filteredItems = this.filteredItems.filter(item =>
        Object.entries(this.filter()!).every(
          ([key, value]) => (item as any)[key] === value
        )
      );
    }

    this.scopedCount = this.filteredItems.length;

    // Apply the optional boolean filter
    const filterOptFn = this.filterOptFn();
    if (filterOptFn && this.filterOptEnabled()) {
      this.filteredItems = this.filteredItems.filter(item => filterOptFn(item));
    }

    // Apply searchText filter
    if (this.searchText) {
      this.filteredItems = this.filteredItems.filter(item => {
        const filterField = this.filterField();
        if (filterField) {
          // Search in specific field
          return this.utilsService.searchInObject((item as any)[filterField], this.searchText);
        } else {
          // Search in the whole object
          return this.utilsService.searchInObject(item, this.searchText);
        }
      });
    }

    // Apply ordering
    if (this.orderBy()) {
      this.filteredItems.sort((a, b) => {
        const aVal = (a as any)[this.orderBy()!];
        const bVal = (b as any)[this.orderBy()!];

        if (aVal == null) return 1;
        if (bVal == null) return -1;

        if (aVal < bVal) return this.orderDesc() ? 1 : -1;
        if (aVal > bVal) return this.orderDesc() ? -1 : 1;
        return 0;
      });
    }

    // A link may point at one item: the interface opens on the page holding it
    const focusItemId = this.focusItemId();
    if (focusItemId && focusItemId !== this.focusedItemId) {
      const position = this.filteredItems.findIndex(item => String((item as any).id) === focusItemId);
      if (position !== -1) {
        this.currentPage = Math.floor(position / this.itemsPerPage()) + 1;
        this.focusedItemId = focusItemId;
      }
    }

    // Ensure current page is valid
    const maxPage = Math.max(Math.ceil(this.filteredItems.length / this.itemsPerPage()), 1);
    if (this.currentPage > maxPage) {
      this.currentPage = maxPage;
    }
    if (this.currentPage < 1) {
      this.currentPage = 1;
    }

    // Pagination
    const start = (this.currentPage - 1) * this.itemsPerPage();
    const end = this.currentPage * this.itemsPerPage();
    this.paginatedItems = [...this.filteredItems.slice(start, end)];
  }

  onSearchUpdate(): void {
    this.currentPage = 1;
    this.update();
  }
}
