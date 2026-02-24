import {Component, EventEmitter, Input, OnInit, Output, inject} from "@angular/core";
import {NgForm, FormsModule} from "@angular/forms";
import {NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {UtilsService} from "@app/shared/services/utils.service";
import {HttpService} from "@app/shared/services/http.service";
import {nodeResolverModel} from "@app/models/resolvers/node-resolver-model";
import {DatePipe, NgClass} from "@angular/common";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {FilterPipe} from "@app/shared/pipes/filter.pipe";
import {statisticalReportResolverModel} from "@app/models/resolvers/statistical-report-resolver-model";
import {StatisticalTemplatesResolver} from "@app/shared/resolvers/statistical-templates.resolver";
import {ChannelFilterOption, DateFilter, StatisticsFilter, statisticalTemplateResolverModel} from "@app/models/resolvers/statistical-template-resolver-model";
import {StatisticalTemplateViewComponent} from "@app/pages/analyst/statistics/statistical-template-view/statistical-template-view.component";
import {IDropdownSettings, NgMultiSelectDropDownModule} from "ng-multiselect-dropdown";
import {DateRangeSelectorComponent} from "@app/shared/components/date-selector/date-selector.component";
import {NgbDate} from "@ng-bootstrap/ng-bootstrap";
import {StatisticsResolver} from "@app/shared/resolvers/statistics.resolver";
import {statisticsResolverModel} from "@app/models/resolvers/statistics-resolver-model";

@Component({
    selector: "src-statistical-report-editor",
    templateUrl: "./statistical-report-editor.component.html",
    standalone: true,
    imports: [DatePipe, FormsModule, NgbTooltipModule, NgClass, TranslatorPipe, FilterPipe, StatisticalTemplateViewComponent, NgMultiSelectDropDownModule, DateRangeSelectorComponent]
})
export class StatisticalReportEditorComponent implements OnInit {
  private httpService = inject(HttpService);
  protected nodeResolver = inject(NodeResolver);
  private utilsService = inject(UtilsService);
  private readonly statisticsResolver = inject(StatisticsResolver);

  @Input() reportData: statisticalReportResolverModel;
  @Input() reportsData: statisticalReportResolverModel[];
  @Input() index: number;
  @Input() editReport: NgForm;
  @Output() dataToParent = new EventEmitter<string>();
  editing = false;
  nodeData: nodeResolverModel;
  templatesData: statisticalTemplateResolverModel[] = [];
  private templatesResolver = inject(StatisticalTemplatesResolver);
  channelDropdownVisible = false;
  channelDropdownModel: ChannelFilterOption[] = [];
  channelDropdownData: ChannelFilterOption[] = [];
  channelFilterActive = false;
  dateFilter: DateFilter | null = null;
  datePicker = false;
  dateModel: { fromDate: NgbDate | null; toDate: NgbDate | null } | null = null;
  currentFilteredData: statisticsResolverModel | null = null;
  filterRevision = 0;
  private filterRequestId = 0;
  private baseStatisticsData: statisticsResolverModel | null = null;

  channelDropdownSettings: IDropdownSettings = {
    singleSelection: false,
    idField: "id",
    textField: "label",
    selectAllText: "Select All",
    unSelectAllText: "UnSelect All",
    itemsShowLimit: 3,
    allowSearchFilter: true,
    enableCheckAll: false
  };

  ngOnInit(): void {
    this.nodeData = this.nodeResolver.dataModel;
    this.templatesData = this.templatesResolver.dataModel;
    this.baseStatisticsData = this.statisticsResolver.dataModel ? {...this.statisticsResolver.dataModel} : null;
    this.initializeFilters();
  }

  get selectedTemplate(): statisticalTemplateResolverModel | null {
    return this.templatesData?.find(t => t.id === this.reportData?.template_id) || null;
  }

  toggleEditing(): void {
    this.editing = !this.editing;
  }

  private initializeFilters(): void {
    this.httpService.requestFilterOptions().subscribe((filterOptions: { channel?: Array<{ id: string | number; label: string | Record<string, string> }> }) => {
      const channels = filterOptions?.channel || [];
      this.channelDropdownData = channels.map((ch) => ({
        id: ch.id,
        label: typeof ch.label === "object" ? ch.label["en"] || Object.values(ch.label)[0] : ch.label
      }));
    });
  }

  toggleChannelFilter(): void {
    this.channelDropdownVisible = !this.channelDropdownVisible;
    this.datePicker = false;
  }

  onChannelFilterChange(): void {
    this.channelFilterActive = this.channelDropdownModel.length > 0;
    this.applyFilters();
  }

  onDateFilterChange(dateRange: { fromDate: string | null; toDate: string | null }): void {
    if (dateRange.fromDate && dateRange.toDate) {
      this.dateFilter = {
        fromDate: dateRange.fromDate,
        toDate: dateRange.toDate
      };
    } else {
      this.dateFilter = null;
    }

    this.applyFilters();
  }

  hasActiveFilters(): boolean {
    return this.channelFilterActive || this.dateFilter !== null;
  }

  clearAllFilters(): void {
    this.channelDropdownModel = [];
    this.channelFilterActive = false;
    this.channelDropdownVisible = false;
    this.dateFilter = null;
    this.datePicker = false;
    this.currentFilteredData = null;

    if (this.baseStatisticsData) {
      this.statisticsResolver.dataModel = {...this.baseStatisticsData};
    }

    this.triggerViewRefresh();
  }

  closeOtherDropdowns(except?: string): void {
    if (except !== "channel") {
      this.channelDropdownVisible = false;
    }

    if (except !== "date") {
      this.datePicker = false;
    }
  }

  getFilterTooltip(filterType: string): string {
    if (filterType !== "channel") {
      return "";
    }

    if (this.channelDropdownModel.length === 0) {
      return "Any Channel";
    }

    return this.channelDropdownModel.map(item => item.label).join(", ");
  }

  getFilterDisplayText(filterType: string): string {
    if (filterType !== "channel") {
      return "Unknown";
    }

    if (this.channelDropdownModel.length === 0) {
      return "Any Channel";
    }

    if (this.channelDropdownModel.length === 1) {
      return this.channelDropdownModel[0].label;
    }

    return `${this.channelDropdownModel.length} selected`;
  }

  private applyFilters(): void {
    const filters: StatisticsFilter = {};

    if (this.dateFilter?.fromDate && this.dateFilter?.toDate) {
      filters.date_from = new Date(this.dateFilter.fromDate).getTime();
      filters.date_to = new Date(this.dateFilter.toDate).getTime();
    }

    if (this.channelDropdownModel.length > 0) {
      filters.channel = this.channelDropdownModel.map(item => item.id || item.label);
    }

    if (!Object.keys(filters).length) {
      this.currentFilteredData = null;
      if (this.baseStatisticsData) {
        this.statisticsResolver.dataModel = {...this.baseStatisticsData};
      }
      this.triggerViewRefresh();
      return;
    }

    const requestId = ++this.filterRequestId;
    this.httpService.requestStatisticsResource(filters).subscribe({
      next: (filteredData: statisticsResolverModel) => {
        if (requestId !== this.filterRequestId) {
          return;
        }
        this.currentFilteredData = filteredData;
        this.statisticsResolver.dataModel = filteredData;
        this.triggerViewRefresh();
      }
    });
  }

  private triggerViewRefresh(): void {
    this.filterRevision += 1;
  }

  deleteReport(report: statisticalReportResolverModel): void {
    this.httpService.requestDeleteStatisticalReport(report.id).subscribe({
      next: () => {
        this.dataToParent.emit();
        this.utilsService.deleteResource(this.reportsData, report);
      },
      error: () => {
      }
    });
  }

  saveReport(report: statisticalReportResolverModel) {
    this.httpService.requestUpdateStatisticalReport(report.id, report).subscribe({});
  }

  async exportReportAsPDF(): Promise<void> {
    const reportRoot = (document.getElementById('report-' + this.index) || document.querySelector(`[name='editReport']`));
    if (!reportRoot) return;

    const printContainer = document.createElement('div');
    printContainer.setAttribute('class', 'report-print-container');

    let templateView: HTMLElement | null = null;
    const configItem = reportRoot.querySelector('.config-item');
    if (configItem) {
      templateView = configItem.querySelector('src-statistical-template-view');
    }

    let contentToPrint: HTMLElement;
    if (templateView) {
      contentToPrint = templateView.cloneNode(true) as HTMLElement;
    } else if (configItem) {
      contentToPrint = configItem.cloneNode(true) as HTMLElement;
    } else {
      contentToPrint = reportRoot.cloneNode(true) as HTMLElement;
    }

    contentToPrint.querySelectorAll('#Content').forEach(el => el.removeAttribute('id'));

    const sourceRoot = (templateView || configItem || reportRoot) as HTMLElement;
    const originalCanvases = sourceRoot?.querySelectorAll('canvas');
    const clonedCanvases = contentToPrint.querySelectorAll('canvas');
    const blobUrls: string[] = [];
    if (originalCanvases && clonedCanvases && originalCanvases.length === clonedCanvases.length) {
      const replacementTasks: Promise<void>[] = [];
      for (let i = 0; i < originalCanvases.length; i++) {
        const origCanvas = originalCanvases[i] as HTMLCanvasElement;
        const cloneCanvas = clonedCanvases[i];
        const replaceTask = new Promise<void>((resolve) => {
          const img = document.createElement('img');
          img.style.maxWidth = '100%';
          img.style.maxHeight = '260px';
          img.style.display = 'block';
          img.style.breakInside = 'avoid';
          img.style.pageBreakInside = 'avoid';
          img.alt = 'Chart';

          const replaceWithFallback = () => {
            cloneCanvas.parentNode?.replaceChild(img, cloneCanvas);
            resolve();
          };

          try {
            origCanvas.toBlob(blob => {
              if (!blob) {
                replaceWithFallback();
                return;
              }
              const blobUrl = URL.createObjectURL(blob);
              blobUrls.push(blobUrl);
              img.onload = () => {
                cloneCanvas.parentNode?.replaceChild(img, cloneCanvas);
                resolve();
              };
              img.onerror = replaceWithFallback;
              img.src = blobUrl;
            }, 'image/png');
          } catch {
            replaceWithFallback();
          }
        });
        replacementTasks.push(replaceTask);
      }
      await Promise.all(replacementTasks);
    }

    printContainer.appendChild(contentToPrint);
    document.body.appendChild(printContainer);
    document.body.classList.add('report-print-mode');

    let cleaned = false;
    const cleanup = () => {
      if (cleaned) return;
      cleaned = true;
      window.removeEventListener('afterprint', cleanup);
      document.body.classList.remove('report-print-mode');
      if (printContainer && printContainer.parentNode) {
        printContainer.parentNode.removeChild(printContainer);
      }
      blobUrls.forEach(url => URL.revokeObjectURL(url));
    };

    window.addEventListener('afterprint', cleanup, { once: true });

    setTimeout(() => {
      window.print();
      setTimeout(cleanup, 1000);
    }, 100);
  }

}
