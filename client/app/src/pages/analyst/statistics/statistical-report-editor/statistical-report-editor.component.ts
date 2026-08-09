import {ChangeDetectorRef, Component, EventEmitter, Input, OnInit, Output, inject} from "@angular/core";
import {NgForm, FormsModule} from "@angular/forms";
import {NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {HttpService} from "@app/shared/services/http.service";
import {nodeResolverModel} from "@app/models/resolvers/node-resolver-model";
import {DatePipe} from "@angular/common";
import {statisticalReportResolverModel} from "@app/models/resolvers/statistical-report-resolver-model";
import {StatisticalTemplatesResolver} from "@app/shared/resolvers/statistical-templates.resolver";
import {ChannelFilterOption, DateFilter, FilterOptionsResponse, StatisticsFilter, statisticalTemplateResolverModel} from "@app/models/resolvers/statistical-template-resolver-model";
import {StatisticalTemplateViewComponent} from "@app/pages/analyst/statistics/statistical-template-view/statistical-template-view.component";
import {StatisticsResolver} from "@app/shared/resolvers/statistics.resolver";
import {statisticsResolverModel} from "@app/models/resolvers/statistics-resolver-model";
import {TranslateModule} from "@ngx-translate/core";

@Component({
    selector: "src-statistical-report-editor",
    templateUrl: "./statistical-report-editor.component.html",
    standalone: true,
    imports: [DatePipe, FormsModule, NgbTooltipModule, StatisticalTemplateViewComponent, TranslateModule]
})
export class StatisticalReportEditorComponent implements OnInit {
  private httpService = inject(HttpService);
  protected nodeResolver = inject(NodeResolver);
  private readonly statisticsResolver = inject(StatisticsResolver);
  private readonly cdr = inject(ChangeDetectorRef);

  @Input() reportData: statisticalReportResolverModel;
  @Input() reportsData: statisticalReportResolverModel[];
  @Input() index: number;
  @Input() filterOptions: FilterOptionsResponse;
  @Input() editReport: NgForm;
  @Output() dataToParent = new EventEmitter<string>();
  editing = false;
  nodeData: nodeResolverModel;
  private templatesResolver = inject(StatisticalTemplatesResolver);
  filterRevision = 0;
  private filterRequestId = 0;
  private baseStatisticsData: statisticsResolverModel | null = null;

  ngOnInit(): void {
    this.nodeData = this.nodeResolver.dataModel;
    this.baseStatisticsData = this.statisticsResolver.dataModel ? {...this.statisticsResolver.dataModel} : null;
  }

  get templatesData(): statisticalTemplateResolverModel[] {
    return this.templatesResolver.dataModel;
  }

  get selectedTemplate(): statisticalTemplateResolverModel | null {
    return this.templatesResolver.dataModel?.find(t => t.id === this.reportData?.template_id) || null;
  }

  private get observation(): { channels?: ChannelFilterOption[]; dateRange?: DateFilter | null } {
    return (this.reportData?.data?.observation as { channels?: ChannelFilterOption[]; dateRange?: DateFilter | null }) || {};
  }

  get observationChannels(): string[] {
    return (this.observation.channels || []).map(channel => channel.label);
  }

  get observationDateRange(): DateFilter | null {
    return this.observation.dateRange || null;
  }

  hasObservation(): boolean {
    return this.observationChannels.length > 0 || this.observationDateRange !== null;
  }

  get isRealtime(): boolean {
    return !!this.reportData?.data?.realtime;
  }

  toggleEditing(): void {
    this.editing = !this.editing;

    if (this.editing) {
      this.loadReportData();
    }
  }

  private loadReportData(): void {
    const data = this.reportData?.data || {};
    const snapshot = data.snapshot as statisticsResolverModel | undefined;

    // Realtime reports are recomputed on every view; non-realtime reports
    // render the snapshot frozen at creation. Legacy reports without a
    // snapshot fall back to recomputation.
    if (data.realtime || !snapshot) {
      this.applyStoredFilters();
      return;
    }

    this.statisticsResolver.dataModel = snapshot;
    this.triggerViewRefresh();
  }

  private applyStoredFilters(): void {
    const storedFilters = (this.reportData?.data?.filters as StatisticsFilter) || {};
    const filters: StatisticsFilter = {};

    if (storedFilters.date_from && storedFilters.date_to) {
      filters.date_from = storedFilters.date_from;
      filters.date_to = storedFilters.date_to;
    }

    if (Array.isArray(storedFilters.channel) && storedFilters.channel.length > 0) {
      filters.channel = storedFilters.channel;
    }

    if (!Object.keys(filters).length) {
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
        this.statisticsResolver.dataModel = filteredData;
        this.triggerViewRefresh();
      }
    });
  }

  private triggerViewRefresh(): void {
    this.filterRevision += 1;
    this.cdr.markForCheck();
  }

  deleteReport(report: statisticalReportResolverModel): void {
    this.httpService.requestDeleteStatisticalReport(report.id).subscribe({
      next: () => {
        this.dataToParent.emit(report.id);
      },
      error: () => {
      }
    });
  }

  exportReportAsPDF(): void {
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
    if (originalCanvases && clonedCanvases && originalCanvases.length === clonedCanvases.length) {
      for (let i = 0; i < originalCanvases.length; i++) {
        const origCanvas = originalCanvases[i] as HTMLCanvasElement;
        const cloneCanvas = clonedCanvases[i] as HTMLCanvasElement;

        // A canvas cloned via cloneNode() loses its bitmap, so repaint the
        // original onto the clone instead of rasterizing it to an <img>.
        // This keeps the chart a <canvas> element and avoids relaxing the
        // Content-Security-Policy img-src directive to allow blob:/data: URLs.
        cloneCanvas.width = origCanvas.width;
        cloneCanvas.height = origCanvas.height;
        cloneCanvas.style.maxWidth = '100%';
        cloneCanvas.style.maxHeight = '260px';
        cloneCanvas.getContext('2d')?.drawImage(origCanvas, 0, 0);
      }
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
    };

    window.addEventListener('afterprint', cleanup, { once: true });

    setTimeout(() => {
      window.print();
      setTimeout(cleanup, 1000);
    }, 100);
  }

}
