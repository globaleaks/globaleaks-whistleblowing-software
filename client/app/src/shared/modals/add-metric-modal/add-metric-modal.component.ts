import {Component, Input, inject, OnInit} from "@angular/core";
import {NgbActiveModal} from "@ng-bootstrap/ng-bootstrap";
import {FormsModule} from "@angular/forms";
import {CommonModule} from "@angular/common";
import {TranslateModule} from "@ngx-translate/core";
import {MetricCard} from "@app/models/resolvers/statistical-template-resolver-model";
import {NgSelectComponent, NgOptionTemplateDirective, NgOptgroupTemplateDirective} from "@ng-select/ng-select";

@Component({
  selector: "src-add-metric-modal",
  templateUrl: "./add-metric-modal.component.html",
  standalone: true,
  imports: [FormsModule, CommonModule, TranslateModule, NgSelectComponent, NgOptionTemplateDirective, NgOptgroupTemplateDirective]
})
export class AddMetricModalComponent implements OnInit {
  private readonly activeModal = inject(NgbActiveModal);

  @Input() availableMetrics: MetricCard[] = [];
  @Input() currentMetricIds: string[] = [];
  @Input() canAddCards = true;
  @Input() canAddCharts = true;

  selectedMetricId = '';
  selectedDisplayType = 'number';

  filteredMetricList: MetricCard[] = [];

  ngOnInit(): void {
    this.updateFilteredMetrics();
  }

  updateFilteredMetrics(): void {
    this.filteredMetricList = this.sortByTitle(
      this.availableMetrics.filter(metric => !this.currentMetricIds.includes(metric.id))
    );
  }

  onMetricSearch(term: string): void {
    const search = term.toLowerCase();
    this.filteredMetricList = this.sortByTitle(
      this.availableMetrics.filter(metric =>
        !this.currentMetricIds.includes(metric.id) &&
        metric.title.toLowerCase().includes(search)
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
    const compatibleTypes = this.getCompatibleDisplayTypes();
    if (compatibleTypes.length > 0) {
      this.selectedDisplayType = compatibleTypes[0];
    }
  }

  selectDisplayType(displayType: string): void {
    this.selectedDisplayType = displayType;
  }

  getSelectedMetric(): MetricCard | undefined {
    return this.availableMetrics.find(m => m.id === this.selectedMetricId);
  }

  getCompatibleDisplayTypes(): string[] {
    const selectedMetric = this.getSelectedMetric();
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

  save(): void {
    if (!this.selectedMetricId || !this.selectedDisplayType) {
      return;
    }

    const selectedMetric = this.availableMetrics.find(m => m.id === this.selectedMetricId);
    if (!selectedMetric) {
      return;
    }

    const isChart = ['pie', 'bar'].includes(this.selectedDisplayType);

    this.activeModal.close({
      metric: selectedMetric,
      chartType: this.selectedDisplayType,
      displayType: isChart ? 'chart' : 'card',
      isChart: isChart
    });
  }

  cancel(): void {
    this.activeModal.dismiss();
  }
}
