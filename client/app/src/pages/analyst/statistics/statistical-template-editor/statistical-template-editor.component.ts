import {CollapsibleCardComponent} from "@app/shared/components/collapsible-card/collapsible-card.component";
import {ChangeDetectorRef, Component, EventEmitter, Input, OnInit, Output, inject} from "@angular/core";
import {NgForm, FormsModule} from "@angular/forms";
import {NgbDropdownModule, NgbModal, NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {HttpService} from "@app/shared/services/http.service";
import {UtilsService} from "@app/shared/services/utils.service";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {CommonModule} from "@angular/common";
import {MetricCard, MetricModalResult, statisticalTemplateResolverModel} from "@app/models/resolvers/statistical-template-resolver-model";
import {ReportTemplateData} from "@app/models/analyst/report-template.model";
import {AddMetricModalComponent} from "@app/shared/modals/add-metric-modal/add-metric-modal.component";
import {ManageMetricModalComponent} from "@app/shared/modals/manage-metric-modal/manage-metric-modal.component";
import {StatisticalMetricsResolver} from "@app/shared/resolvers/statistical-metrics.resolver";
import {TranslateModule} from "@ngx-translate/core";
import {provideCharts, withDefaultRegisterables} from "ng2-charts";
import {StatisticalTemplateViewComponent} from "@app/pages/analyst/statistics/statistical-template-view/statistical-template-view.component";
import {StatisticalTemplateService} from "@app/pages/analyst/statistics/statistical-template-service";

@Component({
  selector: "src-statistical-template-editor",
  templateUrl: "./statistical-template-editor.component.html",
  standalone: true,
  providers: [provideCharts(withDefaultRegisterables())],
  imports: [CollapsibleCardComponent,
    FormsModule,
    NgbTooltipModule,
    CommonModule,
    TranslateModule,
    NgbDropdownModule,
    StatisticalTemplateViewComponent
  ]
})
export class StatisticalTemplateEditorComponent implements OnInit {
  private readonly httpService = inject(HttpService);
  private readonly utilsService = inject(UtilsService);
  private readonly authenticationService = inject(AuthenticationService);
  private readonly modalService = inject(NgbModal);
  private readonly metricsResolver = inject(StatisticalMetricsResolver);
  private readonly templateService = inject(StatisticalTemplateService);
  private readonly cdr = inject(ChangeDetectorRef);

  @Input() templateData!: statisticalTemplateResolverModel;
  @Input() templatesData: statisticalTemplateResolverModel[] = [];
  @Input() index = 0;
  @Input() editTemplate!: NgForm;
  @Output() dataToParent = new EventEmitter<string>();

  editing = false;
  availableMetrics: MetricCard[] = [];
  metricCards: MetricCard[] = [];
  chartMetrics: MetricCard[] = [];

  currentTemplate: ReportTemplateData | null = null;

  ngOnInit(): void {
    this.initializeComponentWithTemplate(this.templateData);
  }

  private initializeComponentWithTemplate(template: statisticalTemplateResolverModel): void {
    this.initializeMetrics();
    this.loadTemplateConfiguration(template);
    this.saveSelectedMetrics();
  }

  private loadTemplateConfiguration(template: statisticalTemplateResolverModel): void {
    const cfg = this.templateService.loadTemplateConfiguration(template, this.availableMetrics);
    this.metricCards = cfg.metricCards;
    this.chartMetrics = cfg.chartMetrics;
  }

  private initializeMetrics(): void {
    this.availableMetrics = this.templateService.createMetricCatalog(this.metricsResolver.dataModel);
  }

  addNewMetric(): void {
    const currentCardIds = this.metricCards.map(card => card.id);
    const currentChartIds = this.chartMetrics.map(chart => chart.id);
    const allCurrentIds = [...currentCardIds, ...currentChartIds];

    const modalRef = this.modalService.open(AddMetricModalComponent, {
      size: "lg",
      backdrop: "static",
      keyboard: false
    });

    modalRef.componentInstance.availableMetrics = this.availableMetrics;
    modalRef.componentInstance.currentMetricIds = allCurrentIds;

    modalRef.result.then((result: MetricModalResult & { displayType?: "card" | "chart" }) => {
      if (!result?.metric) {
        return;
      }

      const newMetricCard: MetricCard = {
        id: result.metric.id,
        title: result.metric.title,
        value: result.metric.value,
        chartType: result.chartType,
        metricType: result.metric.metricType,
        category: result.metric.category,
        compatibleTypes: result.metric.compatibleTypes,
        customData: result.metric.customData
      };

      if (["bar", "pie"].includes(result.chartType)) {
        this.chartMetrics.push(newMetricCard);
      } else {
        this.metricCards.push(newMetricCard);
      }

      this.saveSelectedMetrics();
    }, () => { /* dismissed */ });
  }

  removeMetric(metricId: string): void {
    this.metricCards = this.metricCards.filter(card => card.id !== metricId);
    const chartMetricIndex = this.chartMetrics.findIndex(chart => chart.id === metricId);
    if (chartMetricIndex !== -1) {
      this.chartMetrics.splice(chartMetricIndex, 1);
    }

    this.saveSelectedMetrics();
  }

  canAddMoreMetrics(): boolean {
    const currentCardIds = this.metricCards.map(card => card.id);
    const currentChartIds = this.chartMetrics.map(chart => chart.id);
    const allCurrentIds = [...currentCardIds, ...currentChartIds];
    const availableToAdd = this.availableMetrics.filter(metric => !allCurrentIds.includes(metric.id));

    return availableToAdd.length > 0;
  }

  manageMetric(metricId: string): void {
    let currentItem = this.metricCards.find(card => card.id === metricId);
    let isChart = false;

    if (!currentItem) {
      currentItem = this.chartMetrics.find(chart => chart.id === metricId);
      isChart = true;
    }

    if (!currentItem) {
      return;
    }

    const allCurrentIds = [...this.metricCards.map(card => card.id), ...this.chartMetrics.map(chart => chart.id)];

    const modalRef = this.modalService.open(ManageMetricModalComponent, {
      size: "lg",
      backdrop: "static",
      keyboard: false
    });

    modalRef.componentInstance.availableMetrics = this.availableMetrics;
    modalRef.componentInstance.currentMetricIds = allCurrentIds;
    modalRef.componentInstance.currentMetricCard = currentItem;

    modalRef.result.then((result: MetricModalResult) => {
      if (!result?.metric) {
        return;
      }

      const newMetricItem: MetricCard = {
        id: result.metric.id,
        title: result.metric.title,
        value: result.metric.value,
        chartType: result.chartType,
        metricType: result.metric.metricType,
        category: result.metric.category,
        compatibleTypes: result.metric.compatibleTypes,
        customData: result.metric.customData
      };

      if (isChart) {
        this.chartMetrics = this.chartMetrics.filter(chart => chart.id !== metricId);
      } else {
        this.metricCards = this.metricCards.filter(card => card.id !== metricId);
      }

      if (["bar", "pie"].includes(result.chartType)) {
        this.chartMetrics.push(newMetricItem);
      } else {
        this.metricCards.push(newMetricItem);
      }

      this.saveSelectedMetrics();
    }, () => { /* dismissed */ });
  }

  private buildTemplateData(): ReportTemplateData {
    const existingData = (this.templateData.data || {}) as Partial<ReportTemplateData> & { config?: any };
    const existingConfig = existingData.config || {};

    return {
      ...existingData,
      config: {
        ...existingConfig,
        selectedMetrics: this.metricCards.map(card => ({
          id: card.id,
          title: card.title,
          chartType: card.chartType
        })),
        selectedCharts: this.chartMetrics.map(chart => ({
          id: chart.id,
          title: chart.title,
          chartType: chart.chartType
        }))
      }
    } as ReportTemplateData;
  }

  private saveSelectedMetrics(): void {
    const selectedCardIds = this.metricCards.map(card => card.id);
    const selectedChartIds = this.chartMetrics.map(card => ({id: card.id, chartType: card.chartType}));
    localStorage.setItem("selected_metrics", JSON.stringify(selectedCardIds));
    localStorage.setItem("selected_chart_metrics", JSON.stringify(selectedChartIds));

    this.currentTemplate = this.buildTemplateData();
    this.templateData.data = this.currentTemplate;
    this.templateData = {...this.templateData};
    this.cdr.markForCheck();
  }

  toggleEditing(): void {
    this.editing = !this.editing;
  }

  exportTemplate(template: statisticalTemplateResolverModel): void {
    this.utilsService.saveAs(this.authenticationService, template.label + ".json", "api/analyst/templates/" + template.id);
  }

  deleteTemplate(template: statisticalTemplateResolverModel): void {
    this.httpService.requestDeleteStatisticalTemplate(template.id).subscribe({
      next: () => {
        this.dataToParent.emit(template.id);
      }
    });
  }

  saveTemplate(template: statisticalTemplateResolverModel): void {
    template.data = this.currentTemplate || this.buildTemplateData();
    this.httpService.requestUpdateStatisticalTemplate(template.id, template).subscribe({
      next: (updatedTemplate: statisticalTemplateResolverModel) => {
        this.templateData = updatedTemplate;
        this.currentTemplate = updatedTemplate.data as ReportTemplateData;

        const templateIndex = this.templatesData.findIndex(item => item.id === updatedTemplate.id);
        if (templateIndex !== -1) {
          this.templatesData[templateIndex] = updatedTemplate;
        }

        this.cdr.markForCheck();
      }
    });
  }
}
