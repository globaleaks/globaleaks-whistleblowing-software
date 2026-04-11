import {
  AfterViewInit,
  Component,
  ContentChild,
  inject,
  Input,
  OnChanges,
  SimpleChanges,
  TemplateRef
} from '@angular/core';
import {CommonModule} from '@angular/common';
import {FormsModule} from '@angular/forms';
import {UtilsService} from "@app/shared/services/utils.service";
import {SearchInputComponent} from '@app/shared/components/search/search.component';
import {PaginationComponent} from '@app/shared/components/pagination/pagination.component';

@Component({
  selector: 'app-paginated-interface',
  templateUrl: './paginated-interface.component.html',
  imports: [CommonModule, FormsModule, PaginationComponent, SearchInputComponent],
})
export class PaginatedInterfaceComponent<T> implements AfterViewInit, OnChanges {
  @Input() mode: 'table' | 'simple' = 'simple';
  @Input() items: T[] = [];
  @Input() filterField = '';
  @Input() itemsPerPage = 20;

  /** Optional: filter by key-value pairs */
  @Input() filter?: { [key: string]: any };

  /** Optional boolean filter (toggle) */
  @Input() filterOptLabel?: string;
  @Input() filterOptEnabled? = false;
  @Input() filterOptFn?: (item: T) => boolean;

  /** Optional: order items by field and direction */
  @Input() orderBy?: keyof T;
  @Input() orderDesc = false;

  /** Templates (auto-detected if mode not set) */
  @ContentChild('header') header?: TemplateRef<any>;
  @ContentChild('content') content?: TemplateRef<any>;

  searchText = '';
  currentPage = 1;
  filteredItems: T[] = [];
  paginatedItems: T[] = [];

  private utilsService = inject(UtilsService);

  constructor() {}

  ngAfterViewInit(): void {
    this.update();
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['items'] || changes['filter'] || changes['orderBy'] || changes['orderDesc']) {
      this.update();
    }
  }

  update(): void {
    this.currentPage = 1;
    this.filteredItems = [...this.items];

    // Apply optional filter object
    if (this.filter) {
      this.filteredItems = this.filteredItems.filter(item =>
        Object.entries(this.filter!).every(
          ([key, value]) => (item as any)[key] === value
        )
      );
    }

    // Apply optional boolean filter (toggle)
    if (this.filterOptFn && this.filterOptEnabled) {
      this.filteredItems = this.filteredItems.filter(item =>
        this.filterOptFn!(item)
      );
    }

    // Apply searchText filter
    if (this.searchText) {
      this.filteredItems = this.filteredItems.filter(item => {
        if (this.filterField) {
          // Search in specific field
          return this.utilsService.searchInObject((item as any)[this.filterField], this.searchText);
        } else {
          // Search in the whole object
          return this.utilsService.searchInObject(item, this.searchText);
        }
      });
    }

    // Apply ordering
    if (this.orderBy) {
      this.filteredItems.sort((a, b) => {
        const aVal = (a as any)[this.orderBy!];
        const bVal = (b as any)[this.orderBy!];

        if (aVal == null) return 1;
        if (bVal == null) return -1;

        if (aVal < bVal) return this.orderDesc ? 1 : -1;
        if (aVal > bVal) return this.orderDesc ? -1 : 1;
        return 0;
      });
    }

    // Ensure current page is valid
    const maxPage = Math.max(Math.ceil(this.filteredItems.length / this.itemsPerPage), 1);
    if (this.currentPage > maxPage) {
      this.currentPage = maxPage;
    }

    // Pagination
    const start = (this.currentPage - 1) * this.itemsPerPage;
    const end = this.currentPage * this.itemsPerPage;
    this.paginatedItems = [...this.filteredItems.slice(start, end)];
  }

  onSearchUpdate(): void {
    this.currentPage = 1;
    this.update();
  }
}
