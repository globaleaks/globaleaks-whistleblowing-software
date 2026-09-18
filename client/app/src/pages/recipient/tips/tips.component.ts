import {SearchDashboardComponent} from "@app/shared/components/search-dashboard/search-dashboard.component";
import {SearchDashboardConfigComponent} from "@app/pages/admin/casemanagement/search-dashboard/search-dashboard.component";
import {SearchQuery, emptySearchQuery} from "@app/models/search/search-query";
import {Component, HostListener, OnDestroy, OnInit, TemplateRef, viewChild, inject} from "@angular/core";
import {TranslatePipe} from "@ngx-translate/core";
import {AppConfigService} from "@app/services/root/app-config.service";
import {NgbModal, NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {AppDataService} from "@app/app-data.service";
import {PreferenceResolver} from "@app/shared/resolvers/preference.resolver";
import {RTipsResolver} from "@app/shared/resolvers/r-tips-resolver.service";
import {UtilsService} from "@app/shared/services/utils.service";
import {TranslateService} from "@ngx-translate/core";
import {TokenResource} from "@app/shared/services/token-resource.service";
import {Router, RouterLink} from "@angular/router";
import {rtipResolverModel} from "@app/models/resolvers/rtips-resolver-model";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {concatMap, delay, from, Subscription, tap, timer, switchMap} from "rxjs";
import {formatDate, DatePipe} from "@angular/common";
import {FormsModule} from "@angular/forms";
import {PaginatedInterfaceComponent} from "@app/shared/components/paginated-interface/paginated-interface.component";
import {TableHeaderComponent} from "@app/shared/components/table/table-header.component";
import {TableFilterOption, TableState} from "@app/shared/components/table/table-state";
import {HttpService} from "@app/shared/services/http.service";
import {InsertReportComponent} from "@app/shared/modals/insert-report/insert-report.component";

@Component({
    selector: "src-tips",
    templateUrl: "./tips.component.html",
    standalone: true,
    imports: [SearchDashboardComponent, SearchDashboardConfigComponent, TranslatePipe, DatePipe, FormsModule, NgbTooltipModule, PaginatedInterfaceComponent, RouterLink, TableHeaderComponent]
})
export class TipsComponent implements OnInit, OnDestroy {
  readonly reportSearchDashboard = viewChild(SearchDashboardComponent);
  searchQuery: SearchQuery = emptySearchQuery();
  private searchSubscription?: Subscription;
  private searchDebounceSubscription?: Subscription;
  private reportSearch = "";
  private unreadOnly = false;
  protected authenticationService = inject(AuthenticationService);
  protected httpService = inject(HttpService);
  private readonly appConfigServices = inject(AppConfigService);
  private readonly router = inject(Router);
  protected RTips = inject(RTipsResolver);
  protected preferencesService = inject(PreferenceResolver);
  private readonly modalService = inject(NgbModal);
  protected utils = inject(UtilsService);
  protected appDataService = inject(AppDataService);
  private readonly translateService = inject(TranslateService);
  private readonly tokenResourceService = inject(TokenResource);

  selectedTips: string[] = [];
  index: number;
  date: { year: number; month: number };

  channelOptions: TableFilterOption[] = [];
  statusOptions: TableFilterOption[] = [];
  scoreOptions: TableFilterOption[] = [];

  readonly table = new TableState<rtipResolverModel>({
    serverSide: true,
    onChange: field => this.onTableChange(field),
    orderBy: "creation_date",
    orderDesc: true,
    filters: {
      context_name: {type: "select"},
      submissionStatusStr: {type: "select"},
      score: {type: "select"},
      creation_date: {type: "daterange"},
      update_date: {type: "daterange"},
      expiration_date: {type: "daterange"}
    }
  });

  ngOnInit() {
    if (!this.RTips.dataModel) {
      void this.router.navigate(["/recipient/home"]);
    } else {
      // Reports may reference contexts that are hidden from the public listing;
      // resolve any missing ones so their metadata is available for display.
      this.appConfigServices.loadContexts(this.RTips.dataModel.map(tip => tip.context_id)).subscribe(() => {
        this.processTips();
      });
      this.table.setItems(this.RTips.dataModel);
    }
  }


  ngOnDestroy() {
    this.searchSubscription?.unsubscribe();
    this.searchDebounceSubscription?.unsubscribe();
  }

  openSearchConfiguration(content: TemplateRef<unknown>) {
    this.modalService.open(content, {size: "xl", scrollable: true});
  }

  refreshSearchDashboard() {
    this.reportSearchDashboard()?.loadTabs();
  }

  onSearchQueryChange(query: SearchQuery) {
    this.searchQuery = query;
    const fields: Record<string, string> = {context_name: "context_id", submissionStatusStr: "status", score: "score"};
    for (const [column, field] of Object.entries(fields)) {
      const filter = query.filters.find(item => item.field === field && item.operator === "in");
      this.table.selections[column] = Array.isArray(filter?.value) ?
        filter.value.map(value => ({id: value, label: String(value)})) : [];
    }
    for (const field of ["creation_date", "update_date", "expiration_date"]) {
      const filter = query.filters.find(item => item.field === field && item.operator === "between");
      this.table.ranges[field] = filter ? filter.value as [number, number] : null;
    }
    this.scheduleReportLoad();
  }

  private onTableChange(column?: string) {
    if (column) {
      const fields: Record<string, string> = {context_name: "context_id", submissionStatusStr: "status", score: "score"};
      const field = fields[column] || column;
      const previous = this.searchQuery.filters.find(item => item.field === field);
      const select = this.table.filters[column]?.type === "select";
      const value = select ? (this.table.selections[column] || []).map(item => item.id) : this.table.ranges[column];
      const filters = this.searchQuery.filters.filter(item => item.field !== field);
      if (value?.length) {
        filters.push({
          id: previous?.id || field,
          field,
          operator: select ? "in" : "between",
          value,
          label: previous?.label || field,
          negated: previous?.negated || false
        });
      }
      this.searchQuery = {...this.searchQuery, filters};
    }
    this.scheduleReportLoad();
  }

  onReportListStateChange(state: {type: 'page' | 'search' | 'filter'; page: number; search: string; filterEnabled: boolean}) {
    this.reportSearch = state.search;
    this.unreadOnly = state.filterEnabled;
    if (state.type === 'search') {
      this.scheduleReportLoad();
    } else {
      this.loadReports(state.page);
    }
  }

  private scheduleReportLoad() {
    this.searchDebounceSubscription?.unsubscribe();
    this.searchDebounceSubscription = timer(250).subscribe(() => this.loadReports(1));
  }

  private loadReports(page: number) {
    this.searchDebounceSubscription?.unsubscribe();
    this.searchSubscription?.unsubscribe();
    this.searchSubscription = this.RTips.load({page, search: this.reportSearch, unread: this.unreadOnly,
      sort: this.table.orderBy, descending: this.table.orderDesc, query: structuredClone(this.searchQuery)}).pipe(
      switchMap(() => this.appConfigServices.loadContexts(this.RTips.dataModel.map(tip => tip.context_id)))
    ).subscribe(() => {
      this.selectedTips = [];
      this.processTips();
      this.table.setItems(this.RTips.dataModel);
    });
  }

  selectAll() {
    this.selectedTips = [];
    this.table.result.forEach(tip => {
      if (tip.accessible) {
      this.selectedTips.push(tip.id);
      }
    });
  }

  deselectAll() {
    this.selectedTips = [];
  }

  filterNewOrUpdated = (obj: { updated?: boolean }) => !!obj.updated;

  exportTips() {
    const selectedTips = [...this.selectedTips];
    this.appDataService.updateShowLoadingPanel(true);

    from(selectedTips)
      .pipe(
        concatMap((tipId: string) =>
          from(this.tokenResourceService.getWithProofOfWork()).pipe(
            tap((token: any) => {
              const url = `api/recipient/rtips/${tipId}/export?token=${token.id}:${token.answer}`;
              window.open(url);
            }),
	    delay(500)
          )
        )
      )
      .subscribe({
        error: (error) => {
          console.error("Export failed", error);
          this.appDataService.updateShowLoadingPanel(false);
        },
        complete: () => {
          this.appDataService.updateShowLoadingPanel(false);
        }
      });
  }

  reload() {
    this.loadReports(this.RTips.request.page);
  }

  tipSwitch(id: string): void {
    this.index = this.selectedTips.indexOf(id);
    if (this.index > -1) {
      this.selectedTips.splice(this.index, 1);
    } else {
      this.selectedTips.push(id);
    }
  }

  isSelected(id: string): boolean {
    return this.selectedTips.indexOf(id) !== -1;
  }

  // The report is entered on the site itself: the channel it is filed on is
  // chosen in the modal, which composes the questionnaire of that channel
  enterReport() {
    const modalRef = this.modalService.open(InsertReportComponent, {
      size: 'xl',
      backdrop: 'static',
      keyboard: false
    });
    modalRef.componentInstance.title = "Enter a report";
    modalRef.result.then(
      () => this.reload(),
      () => { /* dismissed */ }
    );
  }

  processTips() {
    const statuses = new Set<string>();
    const channels = new Set<string>();
    const scores = new Set<number>();
    const receiverMap = new Map(this.appDataService.public.receivers.map(r => [r.id, r.name || ""]));

    for (const tip of this.RTips.dataModel) {
      tip.context = this.appDataService.contexts_by_id[tip.context_id];
      tip.context_name = tip.context?.name ?? tip.context_name ?? '';
      // A request reports the outcome of the request itself and not the
      // status of any report
      tip.submissionStatusStr = tip.type === "request" && (tip.allow_transmission || tip.status === "closed") ?
        this.translateService.instant(tip.allow_transmission ? "Authorized" : "Denied") :
        this.utils.getSubmissionStatusText(tip.status, tip.substatus, this.appDataService.submissionStatuses);

      statuses.add(tip.submissionStatusStr);
      channels.add(tip.context_name);
      scores.add(tip.score);
      tip.receiver_names = tip.receiver_ids.map(id => receiverMap.get(id) || "").filter(Boolean).join("\n");
    }

    // The options are matched on the value held by the report, not on their
    // label: the label follows the language of the interface, the value does not
    this.statusOptions = Array.from(statuses, status => ({id: status, label: status}));
    this.channelOptions = Array.from(channels, channel => ({id: channel, label: channel}));
    this.scoreOptions = Array.from(scores, score => ({id: score, label: this.maskScore(score)}));
  }

  maskScore(score: number) {
    if (score === 1) {
      return this.translateService.instant("Low");
    } else if (score === 2) {
      return this.translateService.instant("Medium");
    } else if (score === 3) {
      return this.translateService.instant("High");
    } else {
      return this.translateService.instant("None");
    }
  }

  @HostListener("document:click", ["$event"])
  onClick(event: MouseEvent) {
    const clickedElement = event.target as HTMLElement;
    const isContainerClicked = clickedElement.classList.contains("ngb-datepicker-container") || clickedElement.classList.contains("dropdown-multi-select-container") ||
      clickedElement.closest(".ngb-datepicker-container") !== null || clickedElement.closest(".dropdown-multi-select-container") !== null;
    if (!isContainerClicked) {
      this.table.openFilter = "";
    }
  }


  exportToCsv(): void {
    if (this.searchQuery.filters.length || this.searchQuery.negated) {
      this.httpService.auditSearchExport(this.searchQuery, this.table.result.length).subscribe();
    }
    this.utils.generateCSV('reports', this.getDataCsv());
  }

  getDataCsv(): any[] {
    const output = [...this.table.result];
    return output.map(tip => ({
      id: tip.id,
      progressive: tip.channel_progressive,
      important: tip.important,
      context_name: tip.context_name,
      label: tip.label,
      status: tip.submissionStatusStr,
      creation_date: formatDate(tip.creation_date, 'dd-MM-yyyy HH:mm', 'en-US'),
      update_date: formatDate(tip.update_date, 'dd-MM-yyyy HH:mm', 'en-US'),
      expiration_date: formatDate(tip.expiration_date, 'dd-MM-yyyy HH:mm', 'en-US'),
      last_access: formatDate(tip.last_access, 'dd-MM-yyyy HH:mm', 'en-US'),
      subscription: tip.subscription === 0 ? 'Not subscribed' : tip.subscription === 1 ? 'Subscribed' : 'Sottoscritta successivamente',
      receiver_count: tip.receiver_count
    }));
  }

  getDataCsvHeaders(): string[] {
    return [
      'Id',
      'Sequential',
      'Important',
      'Reminder',
      'Channel',
      'Label',
      'Report Status',
      'Date of Report',
      'Last Update',
      'Expiration date',
      'Last Access',
      'Subscription',
      'Number of Recipients'
    ].map(header => header ? this.translateService.instant(header) : '');
  }
}
