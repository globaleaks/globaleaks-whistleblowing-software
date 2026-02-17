import {Component, Input, OnInit, Output, EventEmitter, inject, OnChanges, SimpleChanges} from "@angular/core";
import {CommonModule} from "@angular/common";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {ChartConfig, MetricCard, statisticalTemplateResolverModel} from "@app/models/resolvers/statistical-template-resolver-model";
import {StatisticsResolver} from "@app/shared/resolvers/statistics.resolver";
import {provideCharts, withDefaultRegisterables, BaseChartDirective} from "ng2-charts";
import {TranslateModule} from "@ngx-translate/core";
import {StatisticalTemplateService} from "@app/pages/analyst/statistics/statistical-template-service";
import {NgbDropdownModule, NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";

@Component({
  selector: 'src-statistical-template-view',
  templateUrl: './statistical-template-view.component.html',
  standalone: true,
  providers: [provideCharts(withDefaultRegisterables())],
  imports: [CommonModule, TranslatorPipe, TranslateModule, BaseChartDirective, NgbDropdownModule, NgbTooltipModule]
})
export class StatisticalTemplateViewComponent implements OnInit, OnChanges {
  protected readonly statisticsResolver = inject(StatisticsResolver);
  protected readonly templateService = inject(StatisticalTemplateService);

  @Input() templateData!: statisticalTemplateResolverModel | null;
  @Input() templatesData: statisticalTemplateResolverModel[] = [];
  @Input() editable = false;
  @Input() refreshKey = 0;

  @Output() removeMetric = new EventEmitter<string>();
  @Output() addNewMetric = new EventEmitter<void>();
  @Output() manageMetric = new EventEmitter<string>();

  chartConfigs: ChartConfig[] = [];
  availableMetrics: MetricCard[] = [];
  metricCards: MetricCard[] = [];
  chartMetrics: MetricCard[] = [];

  ngOnInit(): void {
    this.initializeComponentWithTemplate(this.templateData);
  }

  ngOnChanges(changes: SimpleChanges): void {
    if ((changes['templateData'] && !changes['templateData'].firstChange) ||
        (changes['refreshKey'] && !changes['refreshKey'].firstChange)) {
      this.initializeComponentWithTemplate(this.templateData);
    }
  }

  private initializeComponentWithTemplate(template: statisticalTemplateResolverModel | null): void {
    const dataModel = this.statisticsResolver.dataModel;
    if (!dataModel) {
      this.availableMetrics = [];
      return;
    }

    this.availableMetrics = this.templateService.createMetricCatalog(dataModel);
    const cfg = this.templateService.loadTemplateConfiguration(template, this.availableMetrics);
    this.metricCards = cfg.metricCards;
    this.chartMetrics = cfg.chartMetrics;
    this.chartConfigs = this.templateService.buildChartConfigs(this.chartMetrics, dataModel);
  }

  canAddMoreMetrics(): boolean {
    return this.metricCards.length + this.chartMetrics.length < this.availableMetrics.length;
  }

  getMetricIdFromChartId(chartId: string): string {
    return chartId.replace('chart-', '');
  }

  onRemoveMetric(metricId: string): void {
    this.removeMetric.emit(metricId);
  }

  onAddNewMetric(): void {
    this.addNewMetric.emit();
  }

  onManageMetric(metricId: string): void {
    this.manageMetric.emit(metricId);
  }
}
