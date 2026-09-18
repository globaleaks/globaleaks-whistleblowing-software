import {Component, input, model, ChangeDetectionStrategy} from '@angular/core';
import {TranslatePipe} from "@ngx-translate/core";
import {FormsModule} from '@angular/forms';

@Component({
    changeDetection: ChangeDetectionStrategy.OnPush,
  selector: 'app-search-input',
  standalone: true,
  imports: [TranslatePipe, FormsModule],
  template: `
    <div class="search-input input-group w-auto">
      <label for="search-filter-input" class="visually-hidden">{{ placeholder() | translate }}</label>
      <input
        id="search-filter-input"
        type="search"
        class="form-control"
        [placeholder]="placeholder() | translate"
        [attr.aria-label]="placeholder() | translate"
        [(ngModel)]="value"
      >
      <span class="input-group-text">
        <i class="fas fa-search" aria-hidden="true"></i>
      </span>
    </div>
  `
})
export class SearchInputComponent {
  readonly placeholder = input<string>('Search');
  readonly value = model('');
}
