import { Injectable, inject } from '@angular/core';
import { Observable, BehaviorSubject, of } from 'rxjs';
import { tap } from 'rxjs/operators';
import { HttpService } from '@app/shared/services/http.service';
import { ReportTemplate, ReportTemplateConfig } from '@app/models/analyst/report-template.model';

@Injectable({
  providedIn: 'root'
})
export class ReportTemplateService {
  private httpService = inject(HttpService);
  private templates$ = new BehaviorSubject<ReportTemplate[]>([]);
  
  constructor() {
    this.loadTemplatesFromBackend();
  }
  
  // Template Management
  getTemplates(): Observable<ReportTemplate[]> {
    return this.templates$.asObservable();
  }

  private loadTemplatesFromBackend(): void {
    this.httpService.getTemplates().subscribe({
      next: (templates) => {
        this.templates$.next(templates || []);
      },
      error: () => {
        // Do not fallback; keep current list as-is
        this.templates$.next([]);
      }
    });
  }
  
  getTemplate(id: string): Observable<ReportTemplate | undefined> {
    const template = this.templates$.value.find(t => t.id === id);
    return of(template);
  }
  
  saveTemplate(template: Partial<ReportTemplate>): Observable<ReportTemplate> {
    if (template.id) {
      // Update existing template via HTTP
      const existingTemplate = this.templates$.value.find(t => t.id === template.id);
      if (existingTemplate) {
        const updatedTemplate = { 
          ...existingTemplate, 
          ...template, 
          lastModified: new Date().toISOString()
        } as ReportTemplate;
        
        return this.httpService.updateTemplate(updatedTemplate).pipe(
          tap((serverTemplate) => {
            const templates = this.templates$.value;
            const index = templates.findIndex(t => t.id === template.id);
            if (index >= 0) {
              templates[index] = serverTemplate;
              this.templates$.next([...templates]);
            }
          })
        );
      }
    } else {
      // Create new template via HTTP
      const newTemplate: Partial<ReportTemplate> = {
        name: template.name || 'Untitled Report',
        isPublic: false,
        config: template.config || this.getDefaultConfig()
      };
      
      return this.httpService.createTemplate(newTemplate).pipe(
        tap((serverTemplate) => {
          const templates = this.templates$.value;
          templates.push(serverTemplate);
          this.templates$.next([...templates]);
        })
      );
    }
    
    // Fallback return (shouldn't reach here normally)
    return of(template as ReportTemplate);
  }
  
  deleteTemplate(id: string): Observable<boolean> {
    return this.httpService.deleteTemplate(id).pipe(
      tap(() => {
        const templates = this.templates$.value.filter(t => t.id !== id);
        this.templates$.next(templates);
      }),
      tap(() => true)
    );
  }
  
  private getDefaultConfig(): ReportTemplateConfig {
    return {
      selectedMetrics: [],
      selectedCharts: []
    };
  }
}
