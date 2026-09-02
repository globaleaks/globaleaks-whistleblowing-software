import {Component} from "@angular/core";
import {SearchQuery, emptySearchQuery} from "@app/models/search/search-query";
import {SearchDashboardComponent} from "@app/shared/components/search-dashboard/search-dashboard.component";

@Component({
  selector: "src-configure-search",
  standalone: true,
  imports: [SearchDashboardComponent],
  templateUrl: "./configure-search.component.html"
})
export class ConfigureSearchComponent {
  query: SearchQuery = emptySearchQuery();
}
