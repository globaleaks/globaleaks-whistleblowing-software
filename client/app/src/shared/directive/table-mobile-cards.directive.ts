import {AfterViewInit, Directive, ElementRef, HostBinding, Input, NgZone, OnDestroy, Renderer2} from "@angular/core";

type Mode = 'tips' | 'default';

@Directive({
  selector: "table[appTableMobileCards]",
  standalone: true
})
export class TableMobileCardsDirective implements AfterViewInit, OnDestroy {
  private observer?: MutationObserver;
  private syncScheduled = false;
  private toggleBtn!: HTMLElement;
  private filtersVisible = false;
  private mode: Mode = 'default';

  constructor(private elementRef: ElementRef<HTMLTableElement>, private zone: NgZone, private renderer: Renderer2) {}

  @Input()
  set appTableMobileCards(value: string | null | undefined) {
    this.mode = value === 'tips' ? 'tips' : 'default';
    this.scheduleSync();
  }

  @HostBinding("class.table-mobile-cards")
  get tableMobileCardsClass(): boolean {
    return true;
  }

  ngAfterViewInit(): void {
    this.zone.runOutsideAngular(() => {
      this.observer = new MutationObserver(() => this.scheduleSync());
      this.observer.observe(this.elementRef.nativeElement, {
        childList: true,
        subtree: true
      });
    });

    this.initMobileToggle();
    this.scheduleSync();
  }

  ngOnDestroy(): void {
    this.observer?.disconnect();
  }

  private initMobileToggle(): void {
    if (this.mode !== 'tips') return;

    const table = this.elementRef.nativeElement;
    const wrapper = table.parentElement;
    if (!wrapper) return;

    if (wrapper.querySelector(".mobile-filter-toggle")) return;

    this.toggleBtn = this.renderer.createElement("button");
    this.toggleBtn.innerText = "Filters";

    this.renderer.addClass(this.toggleBtn, "btn");
    this.renderer.addClass(this.toggleBtn, "btn-outline-secondary");
    this.renderer.addClass(this.toggleBtn, "btn-sm");
    this.renderer.addClass(this.toggleBtn, "mb-2");
    this.renderer.addClass(this.toggleBtn, "mobile-filter-toggle");

    this.toggleBtn.addEventListener("click", () => {
      this.filtersVisible = !this.filtersVisible;
      this.updateFilterVisibility();
    });

    this.renderer.insertBefore(wrapper, this.toggleBtn, table);

    window.addEventListener("resize", () => this.updateFilterVisibility());

    this.updateFilterVisibility();
  }

  private updateFilterVisibility(): void {
    const table = this.elementRef.nativeElement;

    if (window.innerWidth <= 768) {
      if (this.mode === 'tips' && this.filtersVisible) {
        this.renderer.addClass(table, "show-filters");
      } else {
        this.renderer.removeClass(table, "show-filters");
      }
    } else {
      this.renderer.removeClass(table, "show-filters");
    }
  }

  private scheduleSync(): void {
    if (this.syncScheduled) return;

    this.syncScheduled = true;

    queueMicrotask(() => {
      this.syncScheduled = false;
      this.syncLabels();
      this.updateFilterVisibility();
    });
  }

  private syncLabels(): void {
    const table = this.elementRef.nativeElement;

    const headers = Array.from(
      table.querySelectorAll("thead tr:last-child th")
    );

    if (!headers.length) return;

    const labels = headers.map((header) =>
      this.getHeaderLabel(header as HTMLElement)
    );

    const rows = Array.from(table.querySelectorAll("tbody tr"));

    for (const row of rows) {
      const cells = Array.from(row.children).filter(
        (child) =>
          child instanceof HTMLTableCellElement &&
          child.tagName === "TD"
      ) as HTMLTableCellElement[];

      cells.forEach((cell, index) => {
        cell.setAttribute("data-label", labels[index] ?? "");
      });
    }
  }

  private getHeaderLabel(header: HTMLElement): string {
    const clone = header.cloneNode(true) as HTMLElement;
    clone.querySelectorAll(".dropdown-multi-select-container, .ngb-datepicker-container, ng-multiselect-dropdown, ngbd-datepicker-range, i, svg").forEach((node) => node.remove());
    return this.normalizeWhitespace(clone.textContent ?? "");
  }

  private normalizeWhitespace(text: string): string {
    return text.replace(/\s+/g, " ").trim();
  }
}