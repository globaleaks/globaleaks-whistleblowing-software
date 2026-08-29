export interface TableFilterOption {
  id: string | number;
  label: string;
}

export type TableFilterType = "select" | "daterange";

export interface TableFilter<T> {
  type: TableFilterType;
  /** Value the filter compares; defaults to the item property named as the filter */
  value?: (item: T) => string | number;
}

export interface TableStateOptions<T> {
  orderBy: keyof T;
  orderDesc?: boolean;
  filters?: Record<string, TableFilter<T>>;
}

/**
 * Sorting and column filtering of a table.
 *
 * The component holds the data and passes `result` to app-paginated-interface,
 * which keeps on owning search, ordering and pagination; the column headers
 * (th[appTableHeader]) drive this state and hold no state of their own.
 */
export class TableState<T> {
  orderBy: keyof T;
  orderDesc: boolean;

  readonly filters: Record<string, TableFilter<T>>;
  readonly selections: Record<string, TableFilterOption[]> = {};
  readonly ranges: Record<string, [number, number] | null> = {};

  /** Key of the column whose filter is open: only one is open at a time */
  openFilter = "";

  /** Filtered items; a new array on every change, so that the interface refreshes */
  result: T[] = [];

  private items: T[] = [];

  constructor(options: TableStateOptions<T>) {
    this.orderBy = options.orderBy;
    this.orderDesc = options.orderDesc || false;
    this.filters = options.filters || {};

    for (const key of Object.keys(this.filters)) {
      this.selections[key] = [];
      this.ranges[key] = null;
    }
  }

  setItems(items: T[]): void {
    this.items = items;
    this.refresh();
  }

  refresh(): void {
    this.result = this.items.filter(item => this.matches(item));
  }

  toggleSort(field: keyof T): void {
    if (this.orderBy === field) {
      this.orderDesc = !this.orderDesc;
    } else {
      this.orderBy = field;
      this.orderDesc = false;
    }
  }

  toggleFilter(key: string): void {
    this.openFilter = this.openFilter === key ? "" : key;
  }

  isFiltered(key: string): boolean {
    return !!this.selections[key]?.length || !!this.ranges[key];
  }

  setSelection(key: string, selection: TableFilterOption[]): void {
    this.selections[key] = selection || [];
    this.refresh();
  }

  setRange(key: string, range: { fromDate: string | null; toDate: string | null }): void {
    this.ranges[key] = range.fromDate && range.toDate ?
      [new Date(range.fromDate).getTime(), new Date(range.toDate).getTime()] :
      null;

    if (!this.ranges[key]) {
      this.openFilter = "";
    }

    this.refresh();
  }

  private matches(item: T): boolean {
    return Object.entries(this.filters).every(([key, filter]) => {
      const value = filter.value ? filter.value(item) : (item as Record<string, any>)[key];

      if (filter.type === "daterange") {
        const range = this.ranges[key];
        if (!range) {
          return true;
        }

        const time = new Date(value).getTime();
        return time >= range[0] && time <= range[1];
      }

      const selection = this.selections[key];
      return !selection?.length || selection.some(option => option.id === value);
    });
  }
}
