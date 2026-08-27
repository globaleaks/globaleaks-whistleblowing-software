import {Injectable} from "@angular/core";
import {SearchFilter, SearchQuery} from "@app/models/search/search-query";

@Injectable({providedIn: "root"})
export class SearchQueryService {
  execute<T>(items: T[], query: SearchQuery, resolveValue: (item: T, field: string) => unknown): T[] {
    if (!query.filters.length) {
      return items;
    }

    return items.filter(item => {
      const matchesAll = query.filters.every(filter => {
        const matches = this.matches(resolveValue(item, filter.field), filter);
        return filter.negated ? !matches : matches;
      });
      return query.negated ? !matchesAll : matchesAll;
    });
  }

  private matches(candidate: unknown, filter: SearchFilter): boolean {
    if (filter.operator === "between") {
      const [from, to] = filter.value as [number, number];
      const timestamp = new Date(candidate as string).getTime();
      return timestamp >= from && timestamp <= to;
    }

    if (filter.operator === "in") {
      const accepted = (filter.value as string[]).map(value => this.normalize(value));
      return this.flatten(candidate).some(value => accepted.includes(this.normalize(value)));
    }

    const term = this.normalize(filter.value);
    return this.flatten(candidate).some(value => this.normalize(value).includes(term));
  }

  private flatten(value: unknown): unknown[] {
    if (Array.isArray(value)) {
      return value.flatMap(item => this.flatten(item));
    }
    if (value && typeof value === "object") {
      return Object.values(value).flatMap(item => this.flatten(item));
    }
    return [value];
  }

  private normalize(value: unknown): string {
    return String(value ?? "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLocaleLowerCase()
      .trim();
  }
}
