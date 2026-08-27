export type SearchFilterOperator = "contains" | "in" | "between";

export interface SearchFilter {
  id: string;
  field: string;
  operator: SearchFilterOperator;
  value: string | string[] | [number, number];
  label: string;
  negated: boolean;
}

export interface SearchQuery {
  negated: boolean;
  filters: SearchFilter[];
}

export interface SearchDashboardTab {
  id: string;
  name: string;
  query: SearchQuery;
  position: number;
}

export interface SearchDashboardState {
  defaults: SearchDashboardTab[];
  personal: SearchDashboardTab[];
}

export const emptySearchQuery = (): SearchQuery => ({
  negated: false,
  filters: []
});
