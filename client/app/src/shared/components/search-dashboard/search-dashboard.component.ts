import {Component, model, OnInit, inject} from "@angular/core";
import {SearchDashboardTab, SearchQuery} from "@app/models/search/search-query";
import {TranslatePipe} from "@ngx-translate/core";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {HttpService} from "@app/shared/services/http.service";

@Component({
  selector: "src-search-dashboard",
  standalone: true,
  imports: [TranslatePipe],
  templateUrl: "./search-dashboard.component.html"
})
export class SearchDashboardComponent implements OnInit {
  private readonly httpService = inject(HttpService);
  private readonly authenticationService = inject(AuthenticationService);
  readonly query = model.required<SearchQuery>();
  defaultTabs: SearchDashboardTab[] = [];
  personalTabs: SearchDashboardTab[] = [];
  activeTabId = "";

  ngOnInit() {
    this.restoreActiveTab();
    this.loadTabs();
  }

  loadTabs() {
    this.httpService.getRecipientDashboard().subscribe(state => {
      this.defaultTabs = state.defaults.sort((a, b) => a.position - b.position);
      this.personalTabs = state.personal.sort((a, b) => a.position - b.position);
      if (this.activeTabId) {
        const tab = [...this.defaultTabs, ...this.personalTabs].find(item => item.id === this.activeTabId);
        if (tab) {
          this.run(tab);
        } else {
          this.clear();
        }
      }
    });
  }

  clear() {
    this.activeTabId = "";
    window.sessionStorage.removeItem(this.getStorageKey());
    this.updateQuery({...this.query(), negated: false, filters: []});
  }

  run(tab: SearchDashboardTab) {
    this.activeTabId = tab.id;
    this.storeActiveTab();
    this.updateQuery(structuredClone(tab.query));
  }

  private getStorageKey(): string {
    return `report-search-tab:${this.authenticationService.getTenantBasePath() || "root"}:${this.authenticationService.session?.user_id}`;
  }

  private storeActiveTab() {
    window.sessionStorage.setItem(this.getStorageKey(), this.activeTabId);
  }

  private restoreActiveTab() {
    this.activeTabId = window.sessionStorage.getItem(this.getStorageKey()) || "";
  }

  private updateQuery(query: SearchQuery) {
    this.query.set(query);
  }
}
