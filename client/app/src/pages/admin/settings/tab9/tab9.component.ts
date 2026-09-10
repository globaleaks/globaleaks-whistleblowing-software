import {Component, EventEmitter, Input, OnInit, Output, inject} from "@angular/core";
import {HttpClient} from "@angular/common/http";
import {FormsModule} from "@angular/forms";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {SearchDashboardTab, SearchFilter, emptySearchQuery} from "@app/models/search/search-query";
import {HttpService} from "@app/shared/services/http.service";

@Component({
  selector: "src-tab9",
  standalone: true,
  imports: [FormsModule, TranslatorPipe],
  templateUrl: "./tab9.component.html"
})
export class Tab9Component implements OnInit {
  private http = inject(HttpClient);
  private httpService = inject(HttpService);
  @Input() recipient = false;
  @Output() tabsChange = new EventEmitter<void>();
  defaultTabs: SearchDashboardTab[] = [];
  tabs: SearchDashboardTab[] = [];
  editingTab?: SearchDashboardTab;
  originalTab?: SearchDashboardTab;
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
    {id: "comment_content", label: "Comment", text: true},
    {id: "file_name", label: "File name", text: true},
    {id: "searchable_content", label: "Report content", text: true},
    {id: "receiver_ids", label: "Assigned recipients"},
    {id: "subscription", label: "Email notifications"}
  ];

  ngOnInit() {
    if (this.recipient) {
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

  addTab() {
    const tab = {
      id: "",
      name: "",
      query: emptySearchQuery(),
      position: this.tabs.length
    };
    this.tabs.push(tab);
    this.startEditing(tab);
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
  }

  updateOperator(filter: SearchFilter, operator: SearchFilter["operator"]) {
    filter.operator = operator;
    if (operator === "in") {
      filter.value = Array.isArray(filter.value) ? filter.value : String(filter.value).split(",").map(value => value.trim()).filter(Boolean);
    } else if (operator === "contains") {
      filter.value = Array.isArray(filter.value) ? filter.value.join(", ") : String(filter.value);
    }
  }

  startEditing(tab: SearchDashboardTab) {
    this.editingTab = tab;
    this.originalTab = structuredClone(tab);
  }

  cancelEditing() {
    if (!this.editingTab || !this.originalTab) {
      return;
    }
    const index = this.tabs.indexOf(this.editingTab);
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
    if (!Array.isArray(filter.value) || !Number.isFinite(filter.value[index])) {
      return "";
    }
    return new Date(filter.value[index]).toISOString().slice(0, 10);
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
  }

  removeFilter(tab: SearchDashboardTab, filter: SearchFilter) {
    tab.query.filters = tab.query.filters.filter(item => item !== filter);
  }

  removeTab(tab: SearchDashboardTab) {
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
    const index = this.tabs.indexOf(tab);
    const target = index + offset;
    if (target < 0 || target >= this.tabs.length) {
      return;
    }
    [this.tabs[index], this.tabs[target]] = [this.tabs[target], this.tabs[index]];
    this.reposition();
    this.save();
  }

  save(done?: () => void) {
    this.reposition();
    if (this.recipient) {
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
    return this.tabs.some(tab => !tab.name.trim() || tab.query.filters.some(filter =>
      (filter.operator === "in" && !Array.isArray(filter.value)) ||
      (filter.operator === "contains" && typeof filter.value !== "string") ||
      (filter.operator === "between" && (!Array.isArray(filter.value) || filter.value.length !== 2 || filter.value.some(value => !Number.isFinite(value))))
    ));
  }

  private reposition() {
    this.tabs.forEach((tab, index) => tab.position = index);
  }
}
