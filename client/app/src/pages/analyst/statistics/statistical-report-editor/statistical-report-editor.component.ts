import {ChangeDetectorRef, Component, ElementRef, Input, OnInit, inject} from "@angular/core";
import {HttpService} from "@app/shared/services/http.service";
import {DatePipe} from "@angular/common";
import {statisticalReportResolverModel} from "@app/models/resolvers/statistical-report-resolver-model";
import {StatisticalTemplatesResolver} from "@app/shared/resolvers/statistical-templates.resolver";
import {ChannelFilterOption, DateFilter, StatisticsFilter, statisticalTemplateResolverModel} from "@app/models/resolvers/statistical-template-resolver-model";
import {StatisticalTemplateViewComponent} from "@app/pages/analyst/statistics/statistical-template-view/statistical-template-view.component";
import {StatisticsResolver} from "@app/shared/resolvers/statistics.resolver";
import {statisticsResolverModel} from "@app/models/resolvers/statistics-resolver-model";
import {TranslateModule} from "@ngx-translate/core";

/**
 * A statistical report, as the table of the reports presents it under its row:
 * the observation it was taken on and the values it froze, laid out by the
 * template it was built on.
 */
@Component({
    selector: "src-statistical-report-editor",
    templateUrl: "./statistical-report-editor.component.html",
    standalone: true,
    imports: [DatePipe, StatisticalTemplateViewComponent, TranslateModule]
})
export class StatisticalReportEditorComponent implements OnInit {
  private httpService = inject(HttpService);
  private readonly statisticsResolver = inject(StatisticsResolver);
  private readonly templatesResolver = inject(StatisticalTemplatesResolver);
  private readonly element = inject(ElementRef);
  private readonly cdr = inject(ChangeDetectorRef);

  @Input() reportData: statisticalReportResolverModel;
  @Input() index: number;

  /** The statistics the report is rendered on: its snapshot or, lacking it, the recomputed ones. */
  viewData: statisticsResolverModel | null = null;
  private filterRequestId = 0;
  private baseStatisticsData: statisticsResolverModel | null = null;

  ngOnInit(): void {
    this.baseStatisticsData = this.statisticsResolver.dataModel ? {...this.statisticsResolver.dataModel} : null;
    this.loadReportData();
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

  private loadReportData(): void {
    const snapshot = this.reportData?.data?.snapshot as statisticsResolverModel | undefined;

    // A report renders the snapshot frozen at its creation; the reports
    // created without a snapshot fall back to recomputation.
    if (!snapshot) {
      this.applyStoredFilters();
      return;
    }

    this.viewData = snapshot;
    this.cdr.markForCheck();
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
      this.viewData = this.baseStatisticsData ? {...this.baseStatisticsData} : null;
      this.cdr.markForCheck();
      return;
    }

    const requestId = ++this.filterRequestId;
    this.httpService.requestStatisticsResource(filters).subscribe({
      next: (filteredData: statisticsResolverModel) => {
        if (requestId !== this.filterRequestId) {
          return;
        }
        this.viewData = filteredData;
        this.cdr.markForCheck();
      }
    });
  }

  exportReportAsPDF(): void {
    const reportRoot = this.element.nativeElement as HTMLElement;
    if (!reportRoot) return;

    const printContainer = document.createElement('div');
    printContainer.setAttribute('class', 'report-print-container');

    const templateView = reportRoot.querySelector('src-statistical-template-view');

    const contentToPrint = (templateView || reportRoot).cloneNode(true) as HTMLElement;

    contentToPrint.querySelectorAll('#Content').forEach(el => el.removeAttribute('id'));

    const sourceRoot = (templateView || reportRoot) as HTMLElement;
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
