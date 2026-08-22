import { Component, input, model } from '@angular/core';
import {
  NgbPagination,
  NgbPaginationPrevious,
  NgbPaginationNext,
  NgbPaginationFirst,
  NgbPaginationLast,
  NgbTooltipModule,
} from '@ng-bootstrap/ng-bootstrap';
import { TranslatorPipe } from '@app/shared/pipes/translate';

@Component({
  selector: 'app-pagination',
  standalone: true,
  templateUrl: './pagination.component.html',
  imports: [
    NgbPagination,
    NgbPaginationPrevious,
    NgbPaginationNext,
    NgbPaginationFirst,
    NgbPaginationLast,
    NgbTooltipModule,
    TranslatorPipe
  ],
})
export class PaginationComponent {
  /** Required: list of items to paginate */
  readonly items = input<any[]>([]);

  /** Current page (two-way bound) */
  readonly currentPage = model(1);

  /** Items per page (default 20) */
  readonly itemsPerPage = input(20);

  /** Emits when page changes */
  onPageChange(page: number) {
    this.currentPage.set(page);
  }
}
