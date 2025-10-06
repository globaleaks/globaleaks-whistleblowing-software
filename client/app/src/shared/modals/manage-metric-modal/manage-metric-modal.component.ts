import {Component, Input, inject, OnInit} from "@angular/core";
import {NgbActiveModal} from "@ng-bootstrap/ng-bootstrap";
import {FormsModule} from "@angular/forms";
import {CommonModule} from "@angular/common";
import {TranslateModule} from "@ngx-translate/core";
import {TranslatorPipe} from "@app/shared/pipes/translate";

interface MetricCard {
  id: string;
  title: string;
  value: number | string;
  chartType?: string;
  category?: 'numeric' | 'comparative' | 'distribution';
  compatibleTypes?: string[];
}

interface ChartType {
  value: string;
  label: string;
  icon: string;
}

@Component({
  selector: "src-manage-metric-modal",
  templateUrl: "./manage-metric-modal.component.html",
  standalone: true,
  imports: [FormsModule, CommonModule, TranslateModule, TranslatorPipe]
})
export class ManageMetricModalComponent implements OnInit {
  private activeModal = inject(NgbActiveModal);

  @Input() availableMetrics: MetricCard[] = [];
  @Input() currentMetricIds: string[] = [];
  @Input() currentMetricCard?: MetricCard;

  selectedMetricId: string = '';
  selectedChartType: string = 'number';
  searchTerm: string = '';

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
  }

  get filteredMetrics(): MetricCard[] {
    // Filter out already selected metrics, except the current one we're editing
    const nonSelectedMetrics = this.availableMetrics.filter(metric =>
      !this.currentMetricIds.includes(metric.id) || metric.id === this.currentMetricCard?.id
    );

    // Then apply search filter if provided
    if (!this.searchTerm.trim()) {
      return nonSelectedMetrics;
    }

    const search = this.searchTerm.toLowerCase();
    return nonSelectedMetrics.filter(metric =>
      metric.title.toLowerCase().includes(search)
    );
  }

  selectMetric(metricId: string): void {
    this.selectedMetricId = metricId;
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
    return ['number', 'percentage']; // Default fallback
  }

  isDisplayTypeCompatible(displayType: string): boolean {
    return this.getCompatibleDisplayTypes().includes(displayType);
  }
}
