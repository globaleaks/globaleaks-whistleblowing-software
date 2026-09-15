import { CommonModule } from '@angular/common';
import { Component, Input, Output, EventEmitter } from '@angular/core';
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
    CommonModule,
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
  @Input() items: any[] = [];

  /** Current page (two-way bound) */
  @Input() currentPage = 1;
  @Output() currentPageChange = new EventEmitter<number>();

  /** Items per page (default 20) */
  @Input() itemsPerPage = 20;
  @Input() collectionSize?: number;

  get itemCount(): number {
    return this.collectionSize ?? this.items.length;
  }

  /** Emits when page changes */
  onPageChange(page: number) {
    this.currentPage = page;
    this.currentPageChange.emit(page);
  }
}
