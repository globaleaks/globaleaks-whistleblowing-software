import {Component, input, OnDestroy, OnInit, output, inject} from "@angular/core";
import {HttpClient} from "@angular/common/http";
import {FormsModule} from "@angular/forms";
import {TranslatePipe} from "@ngx-translate/core";
import {SearchDashboardTab, SearchFilter, emptySearchQuery} from "@app/models/search/search-query";
import {HttpService} from "@app/shared/services/http.service";
import {forkJoin} from "rxjs";
import {NgClass} from "@angular/common";
import {NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";

@Component({
  selector: "src-search-dashboard-config",
  standalone: true,
  imports: [FormsModule, NgClass, NgbTooltipModule, TranslatePipe],
  templateUrl: "./search-dashboard.component.html"
})
export class SearchDashboardConfigComponent implements OnInit, OnDestroy {
  private readonly http = inject(HttpClient);
  private readonly httpService = inject(HttpService);
  readonly recipient = input(false);
  readonly tabsChange = output<void>();
  defaultTabs: SearchDashboardTab[] = [];
  tabs: SearchDashboardTab[] = [];
  editingTab?: SearchDashboardTab;
  originalTab?: SearchDashboardTab;
  showAddTab = false;
  newTabName = "";
  suggestions = new Map<SearchFilter, string[]>();
  invalidValues = new Set<SearchFilter>();
  pendingValues = new Set<SearchFilter>();
  private readonly suggestionTimers = new Map<SearchFilter, ReturnType<typeof setTimeout>>();
  private readonly suggestionTerms = new Map<SearchFilter, string>();
  fields = [
    {id: "creation_date", label: "Submission date", date: true},
    {id: "update_date", label: "Last update", date: true},
    {id: "expiration_date", label: "Expiration date", date: true},
    {id: "status", label: "Status"},
    {id: "substatus", label: "Substatus"},
    {id: "context_id", label: "Channel"},
    {id: "score", label: "Score"},
    {id: "important", label: "Marked as important"},
    {id: "updated", label: "Unread or updated"},
    {id: "file_count", label: "Number of files"},
    {id: "comment_count", label: "Number of comments"},
    {id: "comment_content", label: "Comment", text: true, recipientOnly: true},
    {id: "file_name", label: "File name", text: true, recipientOnly: true},
    {id: "file_type", label: "File type", recipientOnly: true},
    {id: "searchable_content", label: "Report content", text: true, recipientOnly: true},
    {id: "receiver_ids", label: "Assigned recipients"},
    {id: "subscription", label: "Email notifications"}
  ];

  get availableFields() {
    return this.recipient() ? this.fields : this.fields.filter(field => !field.recipientOnly);
  }

  ngOnInit() {
    if (this.recipient()) {
      this.httpService.getRecipientDashboard().subscribe(response => {
        this.defaultTabs = response.defaults.sort((a, b) => a.position - b.position);
        this.tabs = response.personal.sort((a, b) => a.position - b.position);
      });
      return;
    }
    this.http.get<{tabs: SearchDashboardTab[]}>("api/admin/search-dashboard").subscribe(response => {
      this.tabs = response.tabs.sort((a, b) => a.position - b.position);
    });
  }

  ngOnDestroy() {
    this.suggestionTimers.forEach(timer => clearTimeout(timer));
  }

  addTab() {
    const name = this.newTabName.trim();
    if (!name) {
      return;
    }
    const tab = {
      id: "",
      name,
      query: emptySearchQuery(),
      position: this.tabs.length
    };
    this.tabs.push(tab);
    this.newTabName = "";
    this.showAddTab = false;
    this.startEditing(tab);
  }

  toggleAddTab() {
    if (this.editingTab) {
      this.cancelEditing();
    }
    this.showAddTab = !this.showAddTab;
    if (!this.showAddTab) {
      this.newTabName = "";
    }
  }

  addFilter(tab: SearchDashboardTab) {
    tab.query.filters.push({
      id: "",
      field: "status",
      operator: "in",
      value: [],
      label: "Status",
      negated: false
    });
  }

  updateField(filter: SearchFilter, field: string) {
    const definition = this.fields.find(item => item.id === field);
    filter.field = field;
    filter.label = definition?.label ?? field;
    filter.operator = definition?.date ? "between" : definition?.text ? "contains" : "in";
    filter.value = definition?.text ? "" : [];
    this.clearSuggestions(filter);
  }

  updateOperator(filter: SearchFilter, operator: SearchFilter["operator"]) {
    filter.operator = operator;
    if (operator === "in") {
      filter.value = Array.isArray(filter.value) ? filter.value : String(filter.value).split(",").map(value => value.trim()).filter(Boolean);
    } else if (operator === "contains") {
      filter.value = Array.isArray(filter.value) ? filter.value.join(", ") : String(filter.value);
    }
    this.requestSuggestions(filter);
  }

  startEditing(tab: SearchDashboardTab) {
    if (this.editingTab && this.editingTab !== tab) {
      this.cancelEditing();
    }
    this.showAddTab = false;
    this.newTabName = "";
    this.editingTab = tab;
    this.originalTab = structuredClone(tab);
  }

  cancelEditing() {
    if (!this.editingTab || !this.originalTab) {
      return;
    }
    const index = this.tabs.indexOf(this.editingTab);
    this.editingTab.query.filters.forEach(filter => this.clearSuggestions(filter));
    if (this.editingTab.id) {
      this.tabs[index] = this.originalTab;
    } else {
      this.tabs.splice(index, 1);
      this.reposition();
    }
    this.editingTab = undefined;
    this.originalTab = undefined;
  }

  saveEditing() {
    this.save(() => {
      this.editingTab = undefined;
      this.originalTab = undefined;
    });
  }

  isDateField(field: string): boolean {
    return this.fields.find(item => item.id === field)?.date === true;
  }

  dateValue(filter: SearchFilter, index: number): string {
    const value = Array.isArray(filter.value) ? filter.value[index] : undefined;
    if (typeof value !== "number" || !Number.isFinite(value)) {
      return "";
    }
    return new Date(value).toISOString().slice(0, 10);
  }

  updateDateValue(filter: SearchFilter, index: number, value: string) {
    const range = Array.isArray(filter.value) ? [...filter.value] : [];
    range[index] = value ? new Date(`${value}T00:00:00`).getTime() : NaN;
    filter.value = range as [number, number];
  }

  updateValue(filter: SearchFilter, value: string) {
    const values = value.split(",").map(item => item.trim()).filter(Boolean);
    if (filter.operator === "in") {
      filter.value = values;
    } else if (filter.operator === "between") {
      filter.value = values.map(item => new Date(item).getTime()) as [number, number];
    } else {
      filter.value = value;
    }
    this.requestSuggestions(filter);
  }

  selectSuggestion(filter: SearchFilter, suggestion: string) {
    if (filter.operator === "in") {
      const values = Array.isArray(filter.value) ? [...filter.value] : [];
      values[values.length - 1] = suggestion;
      filter.value = values;
    } else {
      filter.value = suggestion;
    }
    this.invalidValues.delete(filter);
    this.suggestions.delete(filter);
  }

  suggestionTerm(filter: SearchFilter): string {
    if (Array.isArray(filter.value)) {
      return String(filter.value[filter.value.length - 1] ?? "").trim();
    }
    return String(filter.value).trim();
  }

  suggestionMinimumLength(filter: SearchFilter): number {
    return filter.field === "file_type" ? 1 : 4;
  }

  removeFilter(tab: SearchDashboardTab, filter: SearchFilter) {
    this.clearSuggestions(filter);
    tab.query.filters = tab.query.filters.filter(item => item !== filter);
  }

  removeTab(tab: SearchDashboardTab) {
    if (this.editingTab && this.editingTab !== tab) {
      this.cancelEditing();
    }
    tab.query.filters.forEach(filter => this.clearSuggestions(filter));
    this.tabs = this.tabs.filter(item => item !== tab);
    this.reposition();
    if (this.editingTab === tab) {
      this.editingTab = undefined;
      this.originalTab = undefined;
    }
    if (tab.id) {
      this.save();
    }
  }

  move(tab: SearchDashboardTab, offset: number) {
    if (this.editingTab) {
      const tabId = tab.id;
      this.cancelEditing();
      if (!tabId) {
        return;
      }
      const restoredTab = this.tabs.find(item => item.id === tabId);
      if (!restoredTab) {
        return;
      }
      tab = restoredTab;
    }
    const index = this.tabs.indexOf(tab);
    const target = index + offset;
    if (index < 0 || target < 0 || target >= this.tabs.length) {
      return;
    }
    [this.tabs[index], this.tabs[target]] = [this.tabs[target]!, this.tabs[index]!];
    this.reposition();
    this.save();
  }

  save(done?: () => void) {
    this.reposition();
    if (this.recipient()) {
      this.httpService.saveRecipientTabs(this.tabs).subscribe(response => {
        this.defaultTabs = response.defaults.sort((a, b) => a.position - b.position);
        this.tabs = response.personal.sort((a, b) => a.position - b.position);
        this.tabsChange.emit();
        done?.();
      });
      return;
    }
    this.http.put<{tabs: SearchDashboardTab[]}>("api/admin/search-dashboard", {tabs: this.tabs}).subscribe(response => {
      this.tabs = response.tabs.sort((a, b) => a.position - b.position);
      this.tabsChange.emit();
      done?.();
    });
  }

  filterValue(filter: SearchFilter): string {
    return Array.isArray(filter.value) ? filter.value.join(", ") : String(filter.value);
  }

  get invalid(): boolean {
    return this.pendingValues.size > 0 || this.tabs.some(tab => !tab.name.trim() || tab.query.filters.some(filter =>
      this.invalidValues.has(filter) ||
      (filter.operator === "in" && !Array.isArray(filter.value)) ||
      (filter.operator === "contains" && typeof filter.value !== "string") ||
      (filter.operator === "between" && (!Array.isArray(filter.value) || filter.value.length !== 2 || filter.value.some(value => !Number.isFinite(value))))
    ));
  }

  private reposition() {
    this.tabs.forEach((tab, index) => tab.position = index);
  }

  private requestSuggestions(filter: SearchFilter) {
    const previousTimer = this.suggestionTimers.get(filter);
    if (previousTimer) {
      clearTimeout(previousTimer);
    }
    this.suggestions.delete(filter);
    this.invalidValues.delete(filter);
    this.pendingValues.delete(filter);
    const value = this.suggestionTerm(filter);
    const minimumLength = this.suggestionMinimumLength(filter);
    const values = (filter.operator === "in" && Array.isArray(filter.value) ? filter.value : [value])
      .map(item => String(item).trim())
      .filter(item => item.length >= minimumLength);
    const validationKey = JSON.stringify(values);
    this.suggestionTerms.set(filter, validationKey);
    if (!values.length || this.isDateField(filter.field)) {
      return;
    }
    this.pendingValues.add(filter);
    this.suggestionTimers.set(filter, setTimeout(() => {
      forkJoin(values.map(item => this.httpService.getSearchSuggestions(
        this.recipient(),
        filter.field,
        filter.operator,
        item
      ))).subscribe({
        next: responses => {
          if (this.suggestionTerms.get(filter) !== validationKey) {
            return;
          }
          this.pendingValues.delete(filter);
          const response = responses[responses.length - 1];
          const verifiableResponses = responses.filter(item => item.verifiable);
          if (!response || !verifiableResponses.length) {
            return;
          }
          this.suggestions.set(filter, response.suggestions);
          if (verifiableResponses.every(item => item.exists)) {
            this.invalidValues.delete(filter);
          } else {
            this.invalidValues.add(filter);
          }
        },
        error: () => {
          this.pendingValues.delete(filter);
        }
      });
    }, 250));
  }

  private clearSuggestions(filter: SearchFilter) {
    const timer = this.suggestionTimers.get(filter);
    if (timer) {
      clearTimeout(timer);
    }
    this.suggestionTimers.delete(filter);
    this.suggestionTerms.delete(filter);
    this.suggestions.delete(filter);
    this.invalidValues.delete(filter);
    this.pendingValues.delete(filter);
  }
}
