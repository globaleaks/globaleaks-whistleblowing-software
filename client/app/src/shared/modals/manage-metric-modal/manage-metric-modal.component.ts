import {Component, Input, inject, OnInit} from "@angular/core";
import {NgbActiveModal} from "@ng-bootstrap/ng-bootstrap";
import {FormsModule} from "@angular/forms";
import {CommonModule} from "@angular/common";
import {TranslateModule} from "@ngx-translate/core";
import {ChartType, MetricCard} from "@app/models/resolvers/statistical-template-resolver-model";
import {NgSelectComponent, NgOptionTemplateDirective, NgOptgroupTemplateDirective} from "@ng-select/ng-select";

@Component({
  selector: "src-manage-metric-modal",
  templateUrl: "./manage-metric-modal.component.html",
  standalone: true,
  imports: [FormsModule, CommonModule, TranslateModule, NgSelectComponent, NgOptionTemplateDirective, NgOptgroupTemplateDirective]
})
export class ManageMetricModalComponent implements OnInit {
  private activeModal = inject(NgbActiveModal);

  @Input() availableMetrics: MetricCard[] = [];
  @Input() currentMetricIds: string[] = [];
  @Input() currentMetricCard?: MetricCard;

  selectedMetricId = '';
  selectedChartType = 'number';
  filteredMetricList: MetricCard[] = [];

  chartTypes: ChartType[] = [
    { value: 'number', label: 'Number', icon: '123' },
    { value: 'percentage', label: 'Percentage', icon: '%' },
    { value: 'pie', label: 'Pie Chart', icon: '📊' },
    { value: 'bar', label: 'Bar Chart', icon: '📈' }
  ];

  ngOnInit() {
    if (this.currentMetricCard) {
      this.selectedMetricId = this.currentMetricCard.id;
      this.selectedChartType = this.currentMetricCard.chartType || 'number';
    }
    this.updateFilteredMetrics()
  }

  updateFilteredMetrics(): void {
    this.filteredMetricList = this.sortByTitle(
      this.availableMetrics.filter(metric =>
        !this.currentMetricIds.includes(metric.id) ||
        metric.id === this.currentMetricCard?.id
      )
    );
  }

  onMetricSearch(term: string): void {
    const searchTerm = term.toLowerCase();
    this.filteredMetricList = this.sortByTitle(
      this.availableMetrics.filter(metric =>
        (!this.currentMetricIds.includes(metric.id) ||
          metric.id === this.currentMetricCard?.id) &&
        metric.title.toLowerCase().includes(searchTerm)
      )
    );
  }

  private sortByTitle(metrics: MetricCard[]): MetricCard[] {
    const groupRank = (group?: string): number => (group === 'Custom' ? 1 : 0);
    return [...metrics].sort((a, b) =>
      groupRank(a.group) - groupRank(b.group) || a.title.localeCompare(b.title)
    );
  }

  selectMetric(metricId: string): void {
    const normalizedMetricId = this.normalizeMetricId(metricId);
    if (!normalizedMetricId) {
      return;
    }

    this.selectedMetricId = normalizedMetricId;
  }

  selectChartType(chartType: string): void {
    this.selectedChartType = chartType;
  }

  save(): void {
    if (this.selectedMetricId && this.selectedChartType) {
      const selectedMetric = this.availableMetrics.find(m => m.id === this.selectedMetricId);
      this.activeModal.close({
        metric: selectedMetric,
        chartType: this.selectedChartType
      });
    }
  }

  cancel(): void {
    this.activeModal.dismiss();
  }

  get hasChanges(): boolean {
    return this.selectedMetricId !== this.currentMetricCard?.id ||
           this.selectedChartType !== (this.currentMetricCard?.chartType || 'number');
  }

  getSelectedMetricTitle(): string {
    const metric = this.availableMetrics.find(m => m.id === this.selectedMetricId);
    return metric ? metric.title : this.selectedMetricId;
  }

  getCompatibleDisplayTypes(): string[] {
    const selectedMetric = this.availableMetrics.find(m => m.id === this.selectedMetricId);
    if (selectedMetric && selectedMetric.compatibleTypes) {
      return selectedMetric.compatibleTypes;
    }
    return ['number', 'percentage'];
  }

  isDisplayTypeCompatible(displayType: string): boolean {
    return this.getCompatibleDisplayTypes().includes(displayType);
  }

  private normalizeMetricId(metricSelection: unknown): string {
    if (typeof metricSelection === 'string') {
      return metricSelection;
    }

    if (metricSelection && typeof metricSelection === 'object' && 'id' in metricSelection) {
      const metricId = (metricSelection as {id?: unknown}).id;
      return typeof metricId === 'string' ? metricId : '';
    }

    return '';
  }
}
