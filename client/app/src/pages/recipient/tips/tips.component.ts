import {Component, HostListener, OnInit, inject} from "@angular/core";
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
import {Answers, rtipResolverModel} from "@app/models/resolvers/rtips-resolver-model";
import {Children} from "@app/models/app/shared-public-model";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {HttpService} from "@app/shared/services/http.service";
import {concatMap, delay, from, tap} from "rxjs";
import {HttpClient, HttpResponse} from "@angular/common/http";
import {formatDate, NgClass, DatePipe} from "@angular/common";
import {FormsModule} from "@angular/forms";
import {DateRangeSelectorComponent} from "@app/shared/components/date-selector/date-selector.component";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {PaginatedInterfaceComponent} from "@app/shared/components/paginated-interface/paginated-interface.component";
import {SearchDashboardComponent} from "@app/shared/components/search-dashboard/search-dashboard.component";
import {SearchableReportContent, SearchFilter, SearchQuery, emptySearchQuery} from "@app/models/search/search-query";
import {SearchQueryService} from "@app/shared/services/search-query.service";

@Component({
    selector: "src-tips",
    templateUrl: "./tips.component.html",
    standalone: true,
    imports: [DatePipe, FormsModule, NgClass, NgMultiSelectDropDownModule, DateRangeSelectorComponent, NgbTooltipModule, PaginatedInterfaceComponent, RouterLink, TranslatorPipe, SearchDashboardComponent]
})
export class TipsComponent implements OnInit {
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
  private searchQueryService = inject(SearchQueryService);

  selectedTips: string[] = [];
  filteredTips: rtipResolverModel[];
  dashboardQueryActive = false;
  searchQuery: SearchQuery = emptySearchQuery();
  searchableContent = new Map<string, SearchableReportContent>();
  searchableContentLoaded = false;
  searchableContentLoading = false;
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
      this.processTips();
    }
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
    this.RTips.reload();
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
    const uniqueKeys: string[] = [];
    const reportUniqueKeys: string[] = [];

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

      if (!uniqueKeys.includes(tip.submissionStatusStr)) {
        uniqueKeys.push(tip.submissionStatusStr);
        this.dropdownStatusData.push({id: this.dropdownStatusData.length + 1, label: tip.submissionStatusStr});
      }

      if (tip.reportModificationStr && !reportUniqueKeys.includes(tip.reportModificationStr)) {
        reportUniqueKeys.push(tip.reportModificationStr);
        this.dropdownReportData.push({id: this.dropdownReportData.length + 1, label: tip.reportModificationStr});
      }

      if (!uniqueKeys.includes(tip.context_name)) {
        uniqueKeys.push(tip.context_name);
        this.dropdownContextData.push({id: this.dropdownContextData.length + 1, label: tip.context_name});
      }

      const scoreLabel = this.maskScore(tip.score);

      if (!uniqueKeys.includes(scoreLabel)) {
        uniqueKeys.push(scoreLabel);
        this.dropdownScoreData.push({id: this.dropdownScoreData.length + 1, label: scoreLabel});
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
    if (!this.dashboardQueryActive) {
      this.processTips();
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
      }
      this.applyFilter();
      return;
    }

    const definitions: Record<string, {id: string; field: string; label: string}> = {
      Score: {id: "score", field: "score", label: "Score"},
      Status: {id: "status", field: "submissionStatusStr", label: "Status"},
      Report: {id: "report", field: "reportModificationStr", label: "Report"},
      Channel: {id: "context", field: "context_name", label: "Channel"}
    };
    const definition = definitions[type];
    if (definition) {
      this.setFilter(definition.id, model.length ? {
        id: definition.id,
        field: definition.field,
        operator: "in",
        value: model.map(item => item.label),
        label: definition.label,
        negated: this.getFilter(definition.id)?.negated ?? false
      } : null);
    }
    this.applyFilter();
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
    if (this.dashboardQueryActive) {
      this.setDateFilter("creation_date", "Report date", this.reportDateFilter);
    }
    this.applyFilter();
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
    if (this.dashboardQueryActive) {
      this.setDateFilter("update_date", "Last update", this.updateDateFilter);
    }
    this.applyFilter();
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
    if (this.dashboardQueryActive) {
      this.setDateFilter("expiration_date", "Expiration date", this.expiryDateFilter);
    }
    this.applyFilter();
  }

  applyFilter() {
    if (!this.dashboardQueryActive) {
      this.filteredTips = this.utils.getStaticFilter(this.RTips.dataModel, this.dropdownStatusModel, "submissionStatusStr", this.translateService);
      this.filteredTips = this.utils.getStaticFilter(this.filteredTips, this.dropdownContextModel, "context_name", this.translateService);
      this.filteredTips = this.utils.getStaticFilter(this.filteredTips, this.dropdownScoreModel, "score", this.translateService);
      this.filteredTips = this.utils.getStaticFilter(this.filteredTips, this.dropdownReportModificationModel, "reportModificationStr", this.translateService);
      this.filteredTips = this.utils.getDateFilter(this.filteredTips, this.reportDateFilter, this.updateDateFilter, this.expiryDateFilter);
      return;
    }

    this.filteredTips = this.searchQueryService.execute(this.RTips.dataModel, this.searchQuery, (tip, field) => {
      if (field === "searchable_content") {
        return [
          tip.progressive,
          tip.label,
          tip.context_name,
          tip.submissionStatusStr,
          tip.receiver_names,
          this.getAnswerSearchContent(tip),
          this.searchableContent.get(tip.id)?.comments,
          this.searchableContent.get(tip.id)?.files
        ];
      }
      if (field === "status") {
        return [tip.status, tip.submissionStatusStr];
      }
      if (field === "context_id") {
        return [tip.context_id, tip.context_name];
      }
      if (field === "score") {
        return this.maskScore(tip.score);
      }
      return tip[field as keyof rtipResolverModel];
    });
  }

  private getAnswerSearchContent(tip: rtipResolverModel): unknown[] {
    const content: unknown[] = [tip.answers];
    const questionnaires = [tip.context?.questionnaire, tip.context?.additional_questionnaire].filter(Boolean);

    for (const questionnaire of questionnaires) {
      for (const step of questionnaire.steps ?? []) {
        this.addAnsweredFields(step.children ?? [], tip.answers, content);
      }
    }

    return content;
  }

  private addAnsweredFields(fields: Children[], answers: Answers, content: unknown[]) {
    for (const field of fields) {
      const fieldAnswers = answers?.[field.id];
      if (fieldAnswers?.length) {
        content.push(field.label, fieldAnswers);
        const selectedValues = new Set(this.searchQueryService.flattenValues(fieldAnswers).map(value => String(value)));
        content.push(field.options?.filter(option => selectedValues.has(option.id)).map(option => option.label));
      }
      if (field.children?.length) {
        this.addAnsweredFields(field.children, answers, content);
      }
    }
  }

  onSearchQueryChange(query: SearchQuery) {
    this.dashboardQueryActive = true;
    this.searchQuery = query;
    this.syncColumnFilters();
    this.applyFilter();
    if (query.filters.some(filter => filter.field === "searchable_content") && !this.searchableContentLoaded && !this.searchableContentLoading) {
      this.searchableContentLoading = true;
      this.httpService.getSearchableReportContent().subscribe({
        next: content => {
          this.searchableContent = new Map(content.map(report => [report.id, report]));
          this.searchableContentLoaded = true;
          this.applyFilter();
        },
        complete: () => this.searchableContentLoading = false,
        error: () => this.searchableContentLoading = false
      });
    }
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
      const values = this.getFilter(id)?.value as string[] | undefined;
      return values ? data.filter(item => values.includes(item.label)) : [];
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
