import {Component, computed, input, model, ChangeDetectionStrategy} from '@angular/core';
import {TranslatePipe} from "@ngx-translate/core";
import {
  NgbPagination,
  NgbPaginationPrevious,
  NgbPaginationNext,
  NgbPaginationFirst,
  NgbPaginationLast,
  NgbTooltipModule,
} from '@ng-bootstrap/ng-bootstrap';

@Component({
    changeDetection: ChangeDetectionStrategy.OnPush,
  selector: 'app-pagination',
  standalone: true,
  templateUrl: './pagination.component.html',
  imports: [TranslatePipe, 
    NgbPagination,
    NgbPaginationPrevious,
    NgbPaginationNext,
    NgbPaginationFirst,
    NgbPaginationLast,
    NgbTooltipModule
  ],
})
export class PaginationComponent {
  /** Required: list of items to paginate */
  readonly items = input<any[]>([]);

  /** Current page (two-way bound) */
  readonly currentPage = model(1);

  /** Items per page (default 20) */
  readonly itemsPerPage = input(20);

  readonly collectionSize = input<number>();
  readonly itemCount = computed(() => this.collectionSize() ?? this.items().length);

  /** Emits when page changes */
  onPageChange(page: number) {
    this.currentPage.set(page);
  }
}
