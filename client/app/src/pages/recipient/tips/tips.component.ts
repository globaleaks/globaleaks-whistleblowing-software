import {Component, HostListener, OnDestroy, OnInit, TemplateRef, ViewChild, inject} from "@angular/core";
import {AppConfigService} from "@app/services/root/app-config.service";
import {NgbDate, NgbModal, NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {AppDataService} from "@app/app-data.service";
import {PreferenceResolver} from "@app/shared/resolvers/preference.resolver";
import {RTipsResolver} from "@app/shared/resolvers/r-tips-resolver.service";
import {UtilsService} from "@app/shared/services/utils.service";
import {TranslateService} from "@ngx-translate/core";
import {IDropdownSettings, NgMultiSelectDropDownModule} from "ng-multiselect-dropdown";
import {TokenResource} from "@app/shared/services/token-resource.service";
import {Router, RouterLink} from "@angular/router";
import {rtipResolverModel} from "@app/models/resolvers/rtips-resolver-model";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {HttpService} from "@app/shared/services/http.service";
import {concatMap, delay, from, Subscription, tap, timer} from "rxjs";
import {HttpClient, HttpResponse} from "@angular/common/http";
import {formatDate, NgClass, DatePipe} from "@angular/common";
import {FormsModule} from "@angular/forms";
import {DateRangeSelectorComponent} from "@app/shared/components/date-selector/date-selector.component";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {PaginatedInterfaceComponent} from "@app/shared/components/paginated-interface/paginated-interface.component";
import {SearchDashboardComponent} from "@app/shared/components/search-dashboard/search-dashboard.component";
import {SearchFilter, SearchQuery, emptySearchQuery} from "@app/models/search/search-query";
import {SearchDashboardConfigComponent} from "@app/pages/admin/casemanagement/search-dashboard/search-dashboard.component";

@Component({
    selector: "src-tips",
    templateUrl: "./tips.component.html",
    standalone: true,
    imports: [DatePipe, FormsModule, NgClass, NgMultiSelectDropDownModule, DateRangeSelectorComponent, NgbTooltipModule, PaginatedInterfaceComponent, RouterLink, TranslatorPipe, SearchDashboardComponent, SearchDashboardConfigComponent]
})
export class TipsComponent implements OnInit, OnDestroy {
  @ViewChild("reportSearchDashboard") reportSearchDashboard?: SearchDashboardComponent;
  private http = inject(HttpClient);
  protected authenticationService = inject(AuthenticationService);
  protected httpService = inject(HttpService);
  private appConfigServices = inject(AppConfigService);
  private router = inject(Router);
  protected RTips = inject(RTipsResolver);
  protected preferencesService = inject(PreferenceResolver);
  private modalService = inject(NgbModal);
  protected utils = inject(UtilsService);
  protected appDataService = inject(AppDataService);
  private translateService = inject(TranslateService);
  private tokenResourceService = inject(TokenResource);

  selectedTips: string[] = [];
  filteredTips: rtipResolverModel[];
  dashboardQueryActive = false;
  searchQuery: SearchQuery = emptySearchQuery();
  searchLoading = false;
  searchSubscription?: Subscription;
  searchDebounceSubscription?: Subscription;
  totalReports = 0;
  currentPage = 1;
  readonly pageSize = 20;
  reportSearch = "";
  unreadOnly = false;
  reportDateFilter: [number, number] | null = null;
  updateDateFilter: [number, number] | null = null;
  expiryDateFilter: [number, number] | null = null;
  reportDateModel: { fromDate: NgbDate | null; toDate: NgbDate | null; } | null = null;
  updateDateModel: { fromDate: NgbDate | null; toDate: NgbDate | null; } | null = null;
  expiryDateModel: { fromDate: NgbDate | null; toDate: NgbDate | null; } | null = null;
  dropdownStatusModel: { id: number; label: string; }[] = [];
  dropdownStatusData: { id: number; label: string; }[] = [];
  dropdownReportModificationModel: { id: number; label: string; }[] = [];
  dropdownReportData: { id: number; label: string; }[] = [];
  dropdownContextModel: { id: number; label: string; }[] = [];
  dropdownContextData: { id: number; label: string; }[] = [];
  dropdownScoreModel: { id: number; label: string; }[] = [];
  dropdownScoreData: { id: number; label: string; }[] = [];
  sortKey: keyof rtipResolverModel = 'creation_date';
  sortReverse = true;
  channelDropdownVisible = false;
  statusDropdownVisible = false;
  scoreDropdownVisible = false;
  reportModificationDropdownVisible = false;
  index: number;
  date: { year: number; month: number };
  reportDatePicker = false;
  lastUpdatePicker = false;
  expirationDatePicker = false;
  dropdownSettings: IDropdownSettings = {
    idField: "id",
    textField: "label",
    itemsShowLimit: 5,
    allowSearchFilter: true,
    selectAllText: this.translateService.instant("Select all"),
    unSelectAllText: this.translateService.instant("Deselect all"),
    searchPlaceholderText: this.translateService.instant("Search")
  };

  ngOnInit() {
    if (!this.RTips.dataModel) {
      this.router.navigate(["/recipient/home"]).then();
    } else {
      this.filteredTips = this.RTips.dataModel;
      this.totalReports = this.RTips.total;
      this.currentPage = this.RTips.request.page;
      this.processTips();
    }
  }

  ngOnDestroy() {
    this.searchDebounceSubscription?.unsubscribe();
    this.searchSubscription?.unsubscribe();
  }

  selectAll() {
    this.selectedTips = [];
    this.filteredTips.forEach(tip => {
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
        next: () => {},
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
    this.loadReports(this.currentPage);
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

  actAsWhistleblower() {
    this.http.get('/api/auth/operatorauthswitch', { observe: 'response' }).subscribe(
      (response: HttpResponse<any>) => {
        if (response.status === 200) {
          window.open(window.location.origin + response.body.redirect);
        }
      },
    );
  }

  processTips() {
    const statusLabels = this.appDataService.submissionStatuses.flatMap(status => {
      const statusLabel = this.translateService.instant(status.label);
      return [statusLabel, ...status.substatuses.map((substatus: {label: string}) => `${statusLabel} – ${substatus.label}`)];
    });
    this.dropdownStatusData = statusLabels.map((label, index) => ({id: index + 1, label}));
    this.dropdownReportData = [
      {id: 1, label: this.translateService.instant("New")},
      {id: 2, label: this.translateService.instant("Updated")}
    ];
    this.dropdownContextData = this.appDataService.public.contexts.map((context, index) => ({
      id: index + 1,
      label: context.name
    }));
    this.dropdownScoreData = [0, 1, 2, 3].map((score, index) => ({id: index + 1, label: this.maskScore(score)}));

    for (const tip of this.RTips.dataModel) {
      tip.context = this.appDataService.contexts_by_id[tip.context_id];
      tip.context_name = tip.context?.name ?? '';
      tip.submissionStatusStr = this.utils.getSubmissionStatusText(tip.status, tip.substatus, this.appDataService.submissionStatuses);

      if (tip.status === 'new') {
        tip.reportModificationStr = this.translateService.instant('New');
      } else if (!tip.updated) {
        tip.reportModificationStr = this.translateService.instant('Updated');
      } else {
        tip.reportModificationStr = '';
      }

      const receiverMap = new Map(this.appDataService.public.receivers.map(r => [r.id, r.name || ""]));
      tip.receiver_names = tip.receiver_ids.map(id => receiverMap.get(id) || "").filter(Boolean).join("\n");
    }
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

  onChanged(model: { id: number; label: string; }[], type: string) {
    const definitions: Record<string, {id: string; field: string; label: string}> = {
      Score: {id: "score", field: "score", label: "Score"},
      Status: {id: "status", field: "status", label: "Status"},
      Report: {id: "report", field: "updated", label: "Report"},
      Channel: {id: "context", field: "context_id", label: "Channel"}
    };
    if (!this.dashboardQueryActive) {
      if (model.length > 0) {
        this.dropdownContextModel = [];
        this.dropdownStatusModel = [];
        this.dropdownScoreModel = [];
        this.dropdownReportModificationModel = [];

        if (type === "Score") {
          this.dropdownScoreModel = model;
        } else if (type === "Status") {
          this.dropdownStatusModel = model;
        } else if (type === "Report") {
          this.dropdownReportModificationModel = model;
        } else if (type === "Channel") {
          this.dropdownContextModel = model;
        }
        const columnFilterIds = Object.values(definitions).map(item => item.id);
        this.searchQuery = {
          ...this.searchQuery,
          filters: this.searchQuery.filters.filter(item => !columnFilterIds.includes(item.id) || item.id === definitions[type].id)
        };
      }
    }

    const definition = definitions[type];
    if (definition) {
      const values = type === "Score" ? model.map(item => item.id - 1) :
        type === "Report" ? model.map(item => item.id === 1 ? "new" : "updated") :
          model.map(item => item.label);
      this.setFilter(definition.id, model.length ? {
        id: definition.id,
        field: definition.field,
        operator: "in",
        value: values,
        label: definition.label,
        negated: this.getFilter(definition.id)?.negated ?? false
      } : null);
    }
    this.scheduleReportLoad();
  }

  checkFilter(filter: { id: number; label: string; }[]) {
    return filter.length > 0;
  };

  resetFiltersStatus() {
    this.channelDropdownVisible = false;
    this.statusDropdownVisible = false;
    this.scoreDropdownVisible = false;
    this.reportModificationDropdownVisible = false;
    this.reportDatePicker = false;
    this.lastUpdatePicker = false;
    this.expirationDatePicker = false;
  }

  toggleReportModificationDropdown() {
    this.resetFiltersStatus();
    this.reportModificationDropdownVisible = !this.reportModificationDropdownVisible;
  }

  toggleChannelDropdown() {
    this.resetFiltersStatus();
    this.channelDropdownVisible = !this.channelDropdownVisible;
  }

  toggleStatusDropdown() {
    this.resetFiltersStatus();
    this.statusDropdownVisible = !this.statusDropdownVisible;
  }

  toggleScoreDropdown() {
    this.resetFiltersStatus();
    this.scoreDropdownVisible = !this.scoreDropdownVisible;
  }

  orderbyCast(data: rtipResolverModel[]): rtipResolverModel[] {
    return data;
  }

  onReportFilterChange(event: { fromDate: string | null; toDate: string | null }) {
    const {fromDate, toDate} = event;
    if (!fromDate && !toDate) {
      this.reportDateFilter = null;
      this.closeAllDatePickers();
    }
    if (fromDate && toDate) {
      this.reportDateFilter = [new Date(fromDate).getTime(), new Date(toDate).getTime()];
    }
    this.setDateFilter("creation_date", "Report date", this.reportDateFilter);
    this.scheduleReportLoad();
  }

  onUpdateFilterChange(event: { fromDate: string | null; toDate: string | null }) {
    const {fromDate, toDate} = event;
    if (!fromDate && !toDate) {
      this.updateDateFilter = null;
      this.closeAllDatePickers();
    }
    if (fromDate && toDate) {
      this.updateDateFilter = [new Date(fromDate).getTime(), new Date(toDate).getTime()];
    }
    this.setDateFilter("update_date", "Last update", this.updateDateFilter);
    this.scheduleReportLoad();
  }

  onExpiryFilterChange(event: { fromDate: string | null; toDate: string | null }) {
    const {fromDate, toDate} = event;
    if (!fromDate && !toDate) {
      this.expiryDateFilter = null;
      this.closeAllDatePickers();
    }
    if (fromDate && toDate) {
      this.expiryDateFilter = [new Date(fromDate).getTime(), new Date(toDate).getTime()];
    }
    this.setDateFilter("expiration_date", "Expiration date", this.expiryDateFilter);
    this.scheduleReportLoad();
  }

  applyFilter() {
    this.filteredTips = this.RTips.dataModel;
  }

  onSearchQueryChange(query: SearchQuery) {
    this.dashboardQueryActive = true;
    this.searchQuery = query;
    this.syncColumnFilters();
    this.scheduleReportLoad();
  }

  private scheduleReportLoad() {
    this.searchDebounceSubscription?.unsubscribe();
    this.searchDebounceSubscription = timer(250).subscribe(() => this.loadReports(1));
  }

  private loadReports(page: number) {
    this.searchDebounceSubscription?.unsubscribe();
    this.searchSubscription?.unsubscribe();
    this.searchLoading = true;
    this.searchSubscription = this.RTips.load({
      page,
      page_size: this.pageSize,
      search: this.reportSearch,
      unread: this.unreadOnly,
      sort: this.sortKey,
      descending: this.sortReverse,
      query: structuredClone(this.searchQuery)
    }).subscribe({
      next: response => {
        this.currentPage = response.page;
        this.totalReports = response.total;
        this.selectedTips = [];
        this.processTips();
        this.applyFilter();
        this.searchLoading = false;
      },
      error: () => {
        this.searchLoading = false;
      }
    });
  }

  onReportListStateChange(state: {
    type: 'page' | 'search' | 'filter';
    page: number;
    search: string;
    filterEnabled: boolean;
  }) {
    this.reportSearch = state.search;
    this.unreadOnly = state.filterEnabled;
    if (state.type === 'search') {
      this.scheduleReportLoad();
      return;
    }
    this.loadReports(state.page);
  }

  changeSort(sort: keyof rtipResolverModel) {
    if (this.sortKey === sort) {
      this.sortReverse = !this.sortReverse;
    } else {
      this.sortKey = sort;
      this.sortReverse = false;
    }
    this.loadReports(1);
  }

  refreshSearchDashboard() {
    this.reportSearchDashboard?.loadTabs();
  }

  openSearchConfiguration(content: TemplateRef<unknown>) {
    this.modalService.open(content, {size: "xl", scrollable: true});
  }

  private setDateFilter(field: string, label: string, value: [number, number] | null) {
    this.setFilter(field, value ? {
      id: field,
      field,
      operator: "between",
      value,
      label,
      negated: this.getFilter(field)?.negated ?? false
    } : null);
  }

  private setFilter(id: string, filter: SearchFilter | null) {
    const filters = this.searchQuery.filters.filter(item => item.id !== id);
    if (filter) {
      filters.push(filter);
    }
    this.searchQuery = {...this.searchQuery, filters};
  }

  private getFilter(id: string): SearchFilter | undefined {
    return this.searchQuery.filters.find(filter => filter.id === id);
  }

  private syncColumnFilters() {
    const selected = (id: string, data: {id: number; label: string}[]) => {
      const values = this.getFilter(id)?.value as Array<string | number> | undefined;
      return values ? data.filter(item => values.includes(item.label) ||
        (id === "score" && values.includes(item.id - 1)) ||
        (id === "report" && values.includes(item.id === 1 ? "new" : "updated"))) : [];
    };
    this.dropdownContextModel = selected("context", this.dropdownContextData);
    this.dropdownStatusModel = selected("status", this.dropdownStatusData);
    this.dropdownScoreModel = selected("score", this.dropdownScoreData);
    this.dropdownReportModificationModel = selected("report", this.dropdownReportData);
    this.reportDateFilter = this.getFilter("creation_date")?.value as [number, number] ?? null;
    this.updateDateFilter = this.getFilter("update_date")?.value as [number, number] ?? null;
    this.expiryDateFilter = this.getFilter("expiration_date")?.value as [number, number] ?? null;
  }

  @HostListener("document:click", ["$event"])
  onClick(event: MouseEvent) {
    const clickedElement = event.target as HTMLElement;
    const isContainerClicked = clickedElement.classList.contains("ngb-datepicker-container") || clickedElement.classList.contains("dropdown-multi-select-container") ||
      clickedElement.closest(".ngb-datepicker-container") !== null || clickedElement.closest(".dropdown-multi-select-container") !== null;
    if (!isContainerClicked) {
      this.closeAllDatePickers();
    }
  }

  closeAllDatePickers() {
    this.reportDatePicker = false;
    this.lastUpdatePicker = false;
    this.expirationDatePicker = false;
    this.scoreDropdownVisible = false;
    this.channelDropdownVisible = false;
    this.statusDropdownVisible = false;
    this.reportDatePicker = false;
    this.lastUpdatePicker = false;
    this.expirationDatePicker = false;
    this.reportModificationDropdownVisible = false;
  }

  exportToCsv(): void {
    if (this.dashboardQueryActive) {
      this.httpService.auditSearchExport(this.searchQuery, this.filteredTips.length).subscribe();
    }
    this.utils.generateCSV('reports', this.getDataCsv());
  }

  getDataCsv(): any[] {
    const output = [...this.filteredTips];
    return output.map(tip => {
      const row: Record<string, string | number | boolean> = {
        progressive: tip.progressive,
        important: tip.important,
        reminder_date: this.utils.isNever(tip.reminder_date) ? '' : formatDate(tip.reminder_date, 'dd-MM-yyyy HH:mm', 'en-US')
      };
      if (this.appDataService.public.contexts.length > 1) {
        row['context_name'] = tip.context_name;
      }
      Object.assign(row, {
        label: tip.label,
        report_status: tip.status === 'new' ? 'New' : tip.updated === false ? 'Updated' : '',
        status: tip.submissionStatusStr,
        creation_date: formatDate(tip.creation_date, 'dd-MM-yyyy HH:mm', 'en-US'),
        update_date: formatDate(tip.update_date, 'dd-MM-yyyy HH:mm', 'en-US'),
        expiration_date: this.utils.isNever(tip.expiration_date) ? '' : formatDate(tip.expiration_date, 'dd-MM-yyyy HH:mm', 'en-US'),
        last_access: formatDate(tip.last_access, 'dd-MM-yyyy HH:mm', 'en-US'),
        comment_count: tip.comment_count,
        file_count: tip.file_count,
        subscription: tip.subscription === 0 ? 'Not subscribed' : 'Subscribed',
        receiver_count: tip.receiver_count
      });
      if (this.appDataService.public.node.enable_scoring_system) {
        row['score'] = this.maskScore(tip.score);
      }
      return row;
    });
  }

  getDataCsvHeaders(): string[] {
    return [
      'Id',
      'Sequential',
      'Important',
      'Reminder',
      'Channel',
      'Label',
      'Report Modification',
      'Report Status',
      'Date of Report',
      'Last Update',
      'Expiration date',
      'Last Access',
      'Number of Comments',
      'Number of Files',
      'Subscription',
      'Number of Recipients'
    ].map(header => header ? this.translateService.instant(header) : '');
  }
}
