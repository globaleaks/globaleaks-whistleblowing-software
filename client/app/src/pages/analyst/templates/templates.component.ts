import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { NgbTooltipModule, NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { TranslateModule, TranslateService } from '@ngx-translate/core';

import { ReportTemplate, ReportTemplateConfig } from '@app/models/analyst/report-template.model';
import { ReportTemplateService } from '@app/services/helper/report-template.service';
import { DeleteConfirmationComponent } from '@app/shared/modals/delete-confirmation/delete-confirmation.component';

@Component({
  selector: 'src-templates',
  templateUrl: './templates.component.html',
  styleUrl: './templates.component.css',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    TranslateModule,
    NgbTooltipModule
  ]
})
export class TemplatesComponent implements OnInit {
  private router = inject(Router);
  private formBuilder = inject(FormBuilder);
  private translateService = inject(TranslateService);
  private templateService = inject(ReportTemplateService);
  private modalService = inject(NgbModal);

  // Component state
  templates: ReportTemplate[] = [];
  isLoading = false;
  selectedTemplate?: ReportTemplate;
  isCreating = false;

  // Sorting and filtering
  sortField: string = 'name';
  sortDirection: 'asc' | 'desc' = 'asc';
  searchTerm: string = '';

  // Form for creating/editing templates
  templateForm: FormGroup;

  constructor() {
    this.templateForm = this.formBuilder.group({
      name: ['', [Validators.required, Validators.minLength(3)]]
    });
  }

  ngOnInit(): void {
    this.loadTemplates();
  }

  // Search and filtering methods
  onSearchChange(): void {
    // Trigger filtering when search term changes
    // The filtering is handled in getFilteredTemplates()
  }

  getFilteredTemplates(): ReportTemplate[] {
    let filtered = [...this.templates];

    // Apply search filter
    if (this.searchTerm && this.searchTerm.trim()) {
      const searchLower = this.searchTerm.toLowerCase();
      filtered = filtered.filter(template =>
        template.name.toLowerCase().includes(searchLower)
      );
    }

    // Apply sorting
    const sorted = filtered.sort((a, b) => {
      let aValue: any, bValue: any;

      switch (this.sortField) {
        case 'name':
          aValue = a.name.toLowerCase();
          bValue = b.name.toLowerCase();
          break;
        // removed 'status' sorting as Status column is not displayed
        case 'createdDate':
          aValue = new Date(a.createdDate).getTime();
          bValue = new Date(b.createdDate).getTime();
          break;
        case 'lastModified':
          aValue = new Date(a.lastModified).getTime();
          bValue = new Date(b.lastModified).getTime();
          break;
        default:
          aValue = a.name.toLowerCase();
          bValue = b.name.toLowerCase();
      }

      if (aValue < bValue) {
        return this.sortDirection === 'asc' ? -1 : 1;
      }
      if (aValue > bValue) {
        return this.sortDirection === 'asc' ? 1 : -1;
      }
      return 0;
    });

    return sorted;
  }

  private loadTemplates(): void {
    this.isLoading = true;
    this.templateService.getTemplates().subscribe({
      next: (templates) => {
        this.templates = templates;
        this.isLoading = false;
      },
      error: () => {
        this.isLoading = false;
      }
    });
  }

  onCreateNew(): void {
    this.isCreating = true;
    this.selectedTemplate = undefined;
    this.templateForm.reset({
      name: ''
    });
  }

  onSaveTemplate(): void {
    if (this.templateForm.valid) {
      const formValue = this.templateForm.value;

      const templateData: Partial<ReportTemplate> = {
        id: this.selectedTemplate?.id,
        name: formValue.name
      };

      this.templateService.saveTemplate(templateData).subscribe({
        next: (savedTemplate) => {
          this.loadTemplates();
          this.cancelEdit();
          // Navigate to the statistics page with the new/updated template in edit mode
          this.router.navigate(['/analyst/statistics/view'], {
            queryParams: { template: savedTemplate.id, mode: 'edit' }
          });
        },
        error: () => {
          // Error handled silently
        }
      });
    }
  }

  onDeleteTemplate(template: ReportTemplate, event: Event): void {
    event.stopPropagation();

    const modalRef = this.modalService.open(DeleteConfirmationComponent, {
      backdrop: 'static',
      keyboard: false
    });

    modalRef.componentInstance.confirmFunction = () => {
      this.templateService.deleteTemplate(template.id).subscribe({
        next: () => {
          this.loadTemplates();
        },
        error: () => {
          // Error handled silently
        }
      });
    };
  }

  cancelEdit(): void {
    this.selectedTemplate = undefined;
    this.isCreating = false;
    this.templateForm.reset();
  }

  // Sorting methods
  sortBy(field: string): void {
    if (this.sortField === field) {
      this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
    } else {
      this.sortField = field;
      this.sortDirection = 'asc';
    }
  }

  // Navigation methods
  viewTemplate(template: ReportTemplate): void {
    this.router.navigate(['/analyst/statistics/view'], {
      queryParams: {
        template: template.id,
        mode: 'view'
      }
    });
  }
}
