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
  selectedDisplayType = 'number';
  searchTerm = '';

  filteredMetricList: MetricCard[] = [];

  ngOnInit(): void {
    this.updateFilteredMetrics();
  }

  updateFilteredMetrics(): void {
    this.filteredMetricList = this.availableMetrics.filter(metric =>
      !this.currentMetricIds.includes(metric.id)
    );
  }

  onSearch(term: string): void {
    const search = term.toLowerCase();
    this.filteredMetricList = this.availableMetrics.filter(metric =>
      !this.currentMetricIds.includes(metric.id) &&
      metric.title.toLowerCase().includes(search)
    );
  }

  selectMetric(metricId: string): void {
    this.selectedMetricId = metricId;
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
