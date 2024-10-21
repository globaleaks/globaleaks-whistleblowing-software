import {Pipe, PipeTransform} from "@angular/core";

@Pipe({
    name: "filter",
    standalone: true
})
export class FilterPipe implements PipeTransform {
  transform(items: any[], field: any, value: any): any[] {
    if (!items) return [];
    if (!value || value.length === 0) return items;

    return items.filter(item => {
      for (const key in item) {
        if (key === field && item[key].includes(value)) {
          return true;
        }
      }
      return false;
    });
  }
}
