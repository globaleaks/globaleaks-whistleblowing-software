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
  description?: string;
  category?: 'numeric' | 'comparative' | 'distribution';
  compatibleTypes?: string[];
}

@Component({
  selector: "src-add-metric-modal",
  templateUrl: "./add-metric-modal.component.html",
  standalone: true,
  imports: [FormsModule, CommonModule, TranslateModule, TranslatorPipe]
})
export class AddMetricModalComponent implements OnInit {
  private activeModal = inject(NgbActiveModal);

  @Input() availableMetrics: MetricCard[] = [];
  @Input() currentMetricIds: string[] = [];
  @Input() canAddCards: boolean = true;
  @Input() canAddCharts: boolean = true;

  selectedMetricId: string = '';
  selectedDisplayType: string = '';
  searchTerm: string = '';

  ngOnInit() {
    // Default to number display
    this.selectedDisplayType = 'number';
  }

  get filteredMetrics(): MetricCard[] {
    // First filter out already selected metrics
    const nonSelectedMetrics = this.availableMetrics.filter(metric => 
      !this.currentMetricIds.includes(metric.id)
    );
    
    // Then apply search filter if provided
    if (!this.searchTerm.trim()) {
      return nonSelectedMetrics;
    }
    
    const search = this.searchTerm.toLowerCase();
    return nonSelectedMetrics.filter(metric =>
      metric.title.toLowerCase().includes(search) ||
      metric.description?.toLowerCase().includes(search)
    );
  }

  selectMetric(metricId: string): void {
    this.selectedMetricId = metricId;
    // Auto-select the first compatible display type
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
    return ['number', 'percentage']; // Default fallback
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
