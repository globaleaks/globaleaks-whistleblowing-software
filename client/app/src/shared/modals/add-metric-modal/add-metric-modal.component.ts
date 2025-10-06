import {Component, Input, inject, OnInit} from "@angular/core";
import {NgbActiveModal} from "@ng-bootstrap/ng-bootstrap";
import {FormsModule} from "@angular/forms";
import {CommonModule} from "@angular/common";
import {TranslateModule} from "@ngx-translate/core";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {HttpService} from "@app/shared/services/http.service";
import {catchError, of} from "rxjs";

interface MetricCard {
  id: string;
  title: string;
  value: number | string;
  description?: string;
  category?: 'numeric' | 'comparative' | 'distribution';
  compatibleTypes?: string[];
  isCustom?: boolean;
  questionnaireId?: string;
  fieldId?: string;
  optionIds?: string[];
}

interface ChartType {
  value: string;
  label: string;
  icon: string;
}

interface Questionnaire {
  id: string;
  name: string;
  steps: any[];
}

interface QuestionField {
  id: string;
  label: string;
  type: string;
  options: FieldOption[];
}

interface FieldOption {
  id: string;
  label: string;
}

@Component({
  selector: "src-add-metric-modal",
  templateUrl: "./add-metric-modal.component.html",
  standalone: true,
  imports: [FormsModule, CommonModule, TranslateModule, TranslatorPipe]
})
export class AddMetricModalComponent implements OnInit {
  private activeModal = inject(NgbActiveModal);
  private httpService = inject(HttpService);

  @Input() availableMetrics: MetricCard[] = [];
  @Input() currentMetricIds: string[] = [];
  @Input() canAddCards: boolean = true;
  @Input() canAddCharts: boolean = true;

  selectedMetricId: string = '';
  selectedDisplayType: string = '';
  searchTerm: string = '';
  
  // Metric type selection
  metricType: 'predefined' | 'custom' = 'predefined';
  
  // Custom metric properties
  questionnaires: Questionnaire[] = [];
  selectedQuestionnaireId: string = '';
  availableFields: QuestionField[] = [];
  selectedFieldId: string = '';
  selectedOptions: string[] = [];
  customMetricName: string = '';

  ngOnInit() {
    // Default to number display
    this.selectedDisplayType = 'number';
    
    // Load questionnaires for custom metrics
    this.loadQuestionnaires();
  }
  
  private loadQuestionnaires(): void {
    // Use the analyst-specific questionnaires endpoint
    this.httpService.requestAnalystQuestionnaires().pipe(
      catchError(() => of([]))
    ).subscribe({
      next: (questionnaires: any[]) => {
        this.questionnaires = questionnaires;
      }
    });
  }
  
  selectMetricType(type: 'predefined' | 'custom'): void {
    this.metricType = type;
    // Reset selections when switching types
    if (type === 'custom') {
      this.selectedMetricId = '';
    } else {
      this.selectedQuestionnaireId = '';
      this.selectedFieldId = '';
      this.selectedOptions = [];
      this.customMetricName = '';
    }
  }
  
  onQuestionnaireSelected(): void {
    const questionnaire = this.questionnaires.find(q => q.id === this.selectedQuestionnaireId);
    if (!questionnaire) {
      this.availableFields = [];
      return;
    }
    
    // Extract multi-choice fields from questionnaire steps
    this.availableFields = [];
    this.extractFieldsFromSteps(questionnaire.steps);
    
    // Reset field and options selection
    this.selectedFieldId = '';
    this.selectedOptions = [];
  }
  
  private extractFieldsFromSteps(steps: any[]): void {
    for (const step of steps) {
      if (step.children && step.children.length > 0) {
        for (const field of step.children) {
          // Check if field is a multi-choice type
          if ((field.type === 'selectbox' || field.type === 'checkbox' || field.type === 'multichoice') 
              && field.options && field.options.length > 0) {
            this.availableFields.push({
              id: field.id,
              label: field.label || 'Unnamed Field',
              type: field.type,
              options: field.options.map((opt: any) => ({
                id: opt.id,
                label: opt.label || 'Unnamed Option'
              }))
            });
          }
        }
      }
    }
  }
  
  onFieldSelected(): void {
    this.selectedOptions = [];
  }
  
  toggleOption(optionId: string): void {
    const index = this.selectedOptions.indexOf(optionId);
    if (index > -1) {
      this.selectedOptions.splice(index, 1);
    } else {
      this.selectedOptions.push(optionId);
    }
  }
  
  isOptionSelected(optionId: string): boolean {
    return this.selectedOptions.includes(optionId);
  }
  
  getSelectedField(): QuestionField | undefined {
    return this.availableFields.find(f => f.id === this.selectedFieldId);
  }
  
  canSaveCustomMetric(): boolean {
    return !!(
      this.selectedQuestionnaireId && 
      this.selectedFieldId && 
      this.selectedOptions.length > 0 &&
      this.customMetricName.trim() &&
      this.selectedDisplayType
    );
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
    if (this.metricType === 'predefined') {
      if (this.selectedMetricId && this.selectedDisplayType) {
        const selectedMetric = this.availableMetrics.find(m => m.id === this.selectedMetricId);
        
        // Determine if it's a card or chart based on display type
        const isChart = ['pie', 'bar'].includes(this.selectedDisplayType);
        
        this.activeModal.close({
          metric: selectedMetric,
          chartType: this.selectedDisplayType,
          displayType: isChart ? 'chart' : 'card'
        });
      }
    } else {
      // Save custom metric
      if (this.canSaveCustomMetric()) {
        const selectedField = this.getSelectedField();
        const questionnaire = this.questionnaires.find(q => q.id === this.selectedQuestionnaireId);
        
        const customMetric: MetricCard = {
          id: `custom_${Date.now()}_${this.selectedFieldId}`,
          title: this.customMetricName,
          value: 0,
          isCustom: true,
          questionnaireId: this.selectedQuestionnaireId,
          fieldId: this.selectedFieldId,
          optionIds: this.selectedOptions,
          category: 'distribution',
          compatibleTypes: ['number', 'percentage', 'bar', 'pie']
        };
        
        const isChart = ['pie', 'bar'].includes(this.selectedDisplayType);
        
        this.activeModal.close({
          metric: customMetric,
          chartType: this.selectedDisplayType,
          displayType: isChart ? 'chart' : 'card'
        });
      }
    }
  }

  cancel(): void {
    this.activeModal.dismiss();
  }
}
