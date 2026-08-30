import {ChangeDetectorRef, Component, ElementRef, Input, OnInit, inject, viewChild} from "@angular/core";
import {NgForm, FormsModule} from "@angular/forms";
import {Constants} from "@app/shared/constants/constants";
import {HttpService} from "@app/shared/services/http.service";
import {UtilsService} from "@app/shared/services/utils.service";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {NgClass} from "@angular/common";
import {StatisticalTemplatesResolver} from "@app/shared/resolvers/statistical-templates.resolver";
import {NewTemplate, statisticalTemplateResolverModel} from "@app/models/resolvers/statistical-template-resolver-model";
import {StatisticalTemplateEditorComponent} from "@app/pages/analyst/statistics/statistical-template-editor/statistical-template-editor.component";
import {PaginatedInterfaceComponent} from "@app/shared/components/paginated-interface/paginated-interface.component";
import {TranslateModule} from "@ngx-translate/core";

@Component({
    selector: "src-statistical-templates-tab",
    templateUrl: "./statistical-templates-tab.component.html",
    standalone: true,
    imports: [StatisticalTemplateEditorComponent, FormsModule, NgbTooltipModule, NgClass, PaginatedInterfaceComponent, TranslateModule]
})
export class StatisticalTemplatesTabComponent implements OnInit {
  private readonly httpService = inject(HttpService);
  private readonly utilsService = inject(UtilsService);
  private readonly authenticationService = inject(AuthenticationService);
  private readonly templatesResolver = inject(StatisticalTemplatesResolver);
  private readonly cdr = inject(ChangeDetectorRef);

  readonly templateUploadInput = viewChild<ElementRef<HTMLInputElement>>("templateUploadInput");

  templatesData: statisticalTemplateResolverModel[] = [];
  @Input() templatesForm!: NgForm;
  @Input() statisticsForm!: NgForm;

  showAddTemplate = false;
  new_template: NewTemplate = {
    label: "",
    data: {}
  };

  protected readonly Constants = Constants;

  /**
   * The template the statistics of the site are presented with: it is chosen by
   * the administrators, the analysts are presented with what it says
   */
  get defaultTemplateId(): string {
    return this.templatesData.find(template => template.default)?.id || "";
  }

  get isAdmin(): boolean {
    return this.authenticationService.session.role === "admin";
  }

  setDefaultTemplate(templateId: string): void {
    this.utilsService.runAdminOperation("set_default_statistical_template", {value: templateId}, false)
                     .subscribe(() => this.reloadTemplates());
  }

  ngOnInit(): void {
    this.templatesData = this.templatesResolver.dataModel;
  }

  toggleAddTemplate(): void {
    this.showAddTemplate = !this.showAddTemplate;
  }

  addTemplate(): void {
    this.httpService.requestCreateStatisticalTemplate(this.new_template).subscribe({
      next: (response) => {
        this.templatesResolver.dataModel.push(response);
        this.templatesData = [...this.templatesResolver.dataModel];
        this.new_template = { label: "", data: {} };
        this.cdr.markForCheck();
      }
    });
  }

  importTemplate(files: FileList | null): void {
    if (!files || files.length === 0) {
      return;
    }

    this.utilsService.readFileAsText(files[0]).subscribe((txt) => {
      this.httpService.requestImportStatisticalTemplate(txt).subscribe({
        next: (response) => {
          this.templatesResolver.dataModel.push(response);
          this.templatesData = [...this.templatesResolver.dataModel];
          this.resetTemplateUploadInput();
          this.cdr.markForCheck();
        },
        error: () => {
          this.resetTemplateUploadInput();
        }
      });
    });
  }

  private resetTemplateUploadInput(): void {
    const templateUploadInput = this.templateUploadInput();
    if (templateUploadInput) {
      templateUploadInput.nativeElement.value = "";
    }
  }

  reloadTemplates(): void {
    this.httpService.requestStatisticalTemplates().subscribe((templates) => {
      this.templatesResolver.dataModel = templates;
      this.templatesData = [...templates];
      this.cdr.markForCheck();
    });
  }

  onTemplateRemoved(templateId: string): void {
    const index = this.templatesResolver.dataModel.findIndex(template => template.id === templateId);
    if (index !== -1) {
      this.templatesResolver.dataModel.splice(index, 1);
    }
    this.templatesData = [...this.templatesResolver.dataModel];
    this.cdr.markForCheck();
  }
}
