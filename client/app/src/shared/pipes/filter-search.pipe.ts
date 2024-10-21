import { Pipe, PipeTransform } from '@angular/core';

@Pipe({
    name: 'search',
    standalone: true
})
export class FilterSearchPipe implements PipeTransform {
  transform(items: any[], searchText: string): any[] {
    if (!items) return [];
    if (!searchText) return items;

    searchText = searchText.toLowerCase();

    return items.filter(item => {
      return Object.keys(item).some(key => {
        const value = item[key];
        return typeof value === 'string' && value.toLowerCase().includes(searchText) ||
               typeof value === 'number' && value.toString().includes(searchText);
      });
    });
  }
}
