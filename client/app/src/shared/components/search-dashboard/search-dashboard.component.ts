import {Component, EventEmitter, Input, OnInit, Output, inject} from "@angular/core";
import {FormsModule} from "@angular/forms";
import {SearchDashboardTab, SearchFilter, SearchQuery} from "@app/models/search/search-query";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {HttpService} from "@app/shared/services/http.service";

@Component({
  selector: "src-search-dashboard",
  standalone: true,
  imports: [FormsModule, TranslatorPipe],
  templateUrl: "./search-dashboard.component.html"
})
export class SearchDashboardComponent implements OnInit {
  private httpService = inject(HttpService);
  @Input({required: true}) query: SearchQuery;
  @Input() mode: "configure" | "apply" = "configure";
  @Output() queryChange = new EventEmitter<SearchQuery>();
  defaultTabs: SearchDashboardTab[] = [];
  personalTabs: SearchDashboardTab[] = [];
  activeTabId = "";
  newTabName = "";

  ngOnInit() {
    this.httpService.getRecipientDashboard().subscribe(state => {
      this.defaultTabs = state.defaults.sort((a, b) => a.position - b.position);
      this.personalTabs = state.personal.sort((a, b) => a.position - b.position);
    });
  }

  get textFilter(): SearchFilter | undefined {
    return this.query.filters.find(filter => filter.id === "text");
  }

  updateText(value: string) {
    const filters = this.query.filters.filter(filter => filter.id !== "text");
    if (value.trim()) {
      filters.unshift({
        id: "text",
        field: "searchable_content",
        operator: "contains",
        value,
        label: "Search",
        negated: this.textFilter?.negated ?? false
      });
    }
    this.emit(filters);
  }

  toggleFilter(filter: SearchFilter) {
    this.emit(this.query.filters.map(item => item.id === filter.id ? {...item, negated: !item.negated} : item));
  }

  removeFilter(filter: SearchFilter) {
    this.emit(this.query.filters.filter(item => item.id !== filter.id));
  }

  toggleOverallNegation() {
    this.activeTabId = "";
    this.updateQuery({...this.query, negated: !this.query.negated});
  }

  clear() {
    this.activeTabId = "";
    this.updateQuery({...this.query, negated: false, filters: []});
  }

  run(tab: SearchDashboardTab) {
    this.activeTabId = tab.id;
    this.updateQuery(structuredClone(tab.query));
  }

  saveCurrent() {
    const name = this.newTabName.trim();
    if (!name) {
      return;
    }
    this.personalTabs.push({
      id: "",
      name,
      query: structuredClone(this.query),
      position: this.personalTabs.length
    });
    this.newTabName = "";
    this.persist();
  }

  rename(tab: SearchDashboardTab, name: string) {
    if (name.trim()) {
      tab.name = name.trim();
      this.persist();
    }
  }

  removeTab(tab: SearchDashboardTab) {
    this.personalTabs = this.personalTabs.filter(item => item !== tab);
    this.reposition();
    this.persist();
  }

  move(tab: SearchDashboardTab, offset: number) {
    const index = this.personalTabs.indexOf(tab);
    const target = index + offset;
    if (target < 0 || target >= this.personalTabs.length) {
      return;
    }
    [this.personalTabs[index], this.personalTabs[target]] = [this.personalTabs[target], this.personalTabs[index]];
    this.reposition();
    this.persist();
  }

  displayValue(filter: SearchFilter): string {
    if (filter.operator === "between") {
      const [from, to] = filter.value as [number, number];
      return `${new Date(from).toLocaleDateString()} – ${new Date(to).toLocaleDateString()}`;
    }
    return Array.isArray(filter.value) ? filter.value.join(", ") : String(filter.value);
  }

  private emit(filters: SearchFilter[]) {
    this.activeTabId = "";
    this.updateQuery({...this.query, filters});
  }

  private updateQuery(query: SearchQuery) {
    this.query = query;
    this.queryChange.emit(query);
  }

  private reposition() {
    this.personalTabs.forEach((tab, index) => tab.position = index);
  }

  private persist() {
    this.httpService.saveRecipientTabs(this.personalTabs).subscribe(state => {
      this.defaultTabs = state.defaults.sort((a, b) => a.position - b.position);
      this.personalTabs = state.personal.sort((a, b) => a.position - b.position);
    });
  }
}
