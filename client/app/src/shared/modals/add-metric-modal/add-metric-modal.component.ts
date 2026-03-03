import {Component, Input, inject, OnInit} from "@angular/core";
import {NgbActiveModal} from "@ng-bootstrap/ng-bootstrap";
import {FormsModule} from "@angular/forms";
import {CommonModule} from "@angular/common";
import {TranslateModule} from "@ngx-translate/core";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {MetricCard} from "@app/models/resolvers/statistical-template-resolver-model";
import {NgSelectComponent, NgOptionTemplateDirective} from "@ng-select/ng-select";

@Component({
  selector: "src-add-metric-modal",
  templateUrl: "./add-metric-modal.component.html",
  standalone: true,
  imports: [FormsModule, CommonModule, TranslateModule, TranslatorPipe, NgSelectComponent, NgOptionTemplateDirective]
})
export class AddMetricModalComponent implements OnInit {
  private activeModal = inject(NgbActiveModal);

  @Input() availableMetrics: MetricCard[] = [];
  @Input() currentMetricIds: string[] = [];
  @Input() canAddCards: boolean = true;
  @Input() canAddCharts: boolean = true;

  selectedMetricId = '';
  selectedStandardMetricId = '';
  selectedTemplateMetricId = '';
  selectedDisplayType = 'number';

  filteredStandardMetricList: MetricCard[] = [];
  filteredTemplateMetricList: MetricCard[] = [];

  ngOnInit(): void {
    this.updateFilteredMetrics();
  }

  updateFilteredMetrics(): void {
    const metricsToAdd = this.availableMetrics.filter(metric => !this.currentMetricIds.includes(metric.id));
    this.filteredStandardMetricList = metricsToAdd.filter(metric => !this.isQuestionTemplateMetric(metric));
    this.filteredTemplateMetricList = metricsToAdd.filter(metric => this.isQuestionTemplateMetric(metric));
  }

  onStandardMetricSearch(term: string): void {
    const search = term.toLowerCase();
    this.filteredStandardMetricList = this.availableMetrics.filter(metric =>
      !this.currentMetricIds.includes(metric.id) &&
      !this.isQuestionTemplateMetric(metric) &&
      metric.title.toLowerCase().includes(search)
    );
  }

  onTemplateMetricSearch(term: string): void {
    const search = term.toLowerCase();
    this.filteredTemplateMetricList = this.availableMetrics.filter(metric =>
      !this.currentMetricIds.includes(metric.id) &&
      this.isQuestionTemplateMetric(metric) &&
      metric.title.toLowerCase().includes(search)
    );
  }

  selectStandardMetric(metricId: string): void {
    const normalizedMetricId = this.normalizeMetricId(metricId);
    if (!normalizedMetricId) {
      return;
    }

    this.selectedStandardMetricId = normalizedMetricId;
    this.selectedTemplateMetricId = '';
    this.selectedMetricId = normalizedMetricId;
    const compatibleTypes = this.getCompatibleDisplayTypes();
    if (compatibleTypes.length > 0) {
      this.selectedDisplayType = compatibleTypes[0];
    }
  }

  selectTemplateMetric(metricId: string): void {
    const normalizedMetricId = this.normalizeMetricId(metricId);
    if (!normalizedMetricId) {
      return;
    }

    this.selectedTemplateMetricId = normalizedMetricId;
    this.selectedStandardMetricId = '';
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

  isQuestionTemplateMetric(metric?: MetricCard): boolean {
    return metric?.metricType === 'question_template_dropdown';
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
