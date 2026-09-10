import {Component, EventEmitter, Input, OnInit, Output, inject} from "@angular/core";
import {SearchDashboardTab, SearchQuery} from "@app/models/search/search-query";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {HttpService} from "@app/shared/services/http.service";

@Component({
  selector: "src-search-dashboard",
  standalone: true,
  imports: [TranslatorPipe],
  templateUrl: "./search-dashboard.component.html"
})
export class SearchDashboardComponent implements OnInit {
  private httpService = inject(HttpService);
  @Input({required: true}) query: SearchQuery;
  @Output() queryChange = new EventEmitter<SearchQuery>();
  defaultTabs: SearchDashboardTab[] = [];
  personalTabs: SearchDashboardTab[] = [];
  activeTabId = "";

  ngOnInit() {
    this.loadTabs();
  }

  loadTabs() {
    this.httpService.getRecipientDashboard().subscribe(state => {
      this.defaultTabs = state.defaults.sort((a, b) => a.position - b.position);
      this.personalTabs = state.personal.sort((a, b) => a.position - b.position);
    });
  }

  clear() {
    this.activeTabId = "";
    this.updateQuery({...this.query, negated: false, filters: []});
  }

  run(tab: SearchDashboardTab) {
    this.activeTabId = tab.id;
    this.updateQuery(structuredClone(tab.query));
  }

  private updateQuery(query: SearchQuery) {
    this.query = query;
    this.queryChange.emit(query);
  }
}
