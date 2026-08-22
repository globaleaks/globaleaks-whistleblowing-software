import {Component, input, model} from '@angular/core';
import {FormsModule} from '@angular/forms';
import {TranslatorPipe} from "@app/shared/pipes/translate";

@Component({
  selector: 'app-search-input',
  standalone: true,
  imports: [FormsModule, TranslatorPipe],
  template: `
    <div class="search-input input-group input-group-sm w-auto">
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
