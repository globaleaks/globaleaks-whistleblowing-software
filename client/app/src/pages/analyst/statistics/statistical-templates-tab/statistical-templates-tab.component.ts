import {Component, Input, OnInit, inject} from "@angular/core";
import {NgForm, FormsModule} from "@angular/forms";
import {Constants} from "@app/shared/constants/constants";
import {HttpService} from "@app/shared/services/http.service";
import {NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {NgClass} from "@angular/common";
import {StatisticalTemplatesResolver} from "@app/shared/resolvers/statistical-templates.resolver";
import {FilterOption, FilterOptionsResponse, NewTemplate, statisticalTemplateResolverModel} from "@app/models/resolvers/statistical-template-resolver-model";
import {StatisticalTemplateEditorComponent} from "@app/pages/analyst/statistics/statistical-template-editor/statistical-template-editor.component";

@Component({
    selector: "src-statistical-templates-tab",
    templateUrl: "./statistical-templates-tab.component.html",
    standalone: true,
    imports: [StatisticalTemplateEditorComponent, FormsModule, NgbTooltipModule, NgClass, TranslatorPipe]
})
export class StatisticalTemplatesTabComponent implements OnInit {
  private readonly httpService = inject(HttpService);
  private readonly templatesResolver = inject(StatisticalTemplatesResolver);
  
  templatesData: statisticalTemplateResolverModel[] = [];
  filteredTemplatesData: statisticalTemplateResolverModel[] = [];
  @Input() templatesForm!: NgForm;
  @Input() statisticsForm!: NgForm;
  searchTerm = "";

  showAddTemplate = false;
  new_template: NewTemplate = {
    label: "",
    data: {}
  };

  protected readonly Constants = Constants;
  filterOptions: FilterOptionsResponse;

  ngOnInit(): void {
    this.templatesData = this.templatesResolver.dataModel;
    this.filteredTemplatesData = this.templatesData;
    this.httpService.requestFilterOptions().subscribe((filterOptions: FilterOptionsResponse) => {
      if (filterOptions && Array.isArray(filterOptions.channel)) {
        filterOptions.channel = filterOptions.channel.map((ch: FilterOption & { label: string | Record<string, string> }): FilterOption => ({
          id: ch.id,
          label: typeof ch.label === "object" ? ch.label["en"] || Object.values(ch.label)[0] : ch.label
        }));
      }
      this.filterOptions = filterOptions;
    });
  }

  toggleAddTemplate(): void {
    this.showAddTemplate = !this.showAddTemplate;
  }

  onSearchChange(): void {
    const term = this.searchTerm.toLowerCase().trim();
    
    if (!term) {
      this.filteredTemplatesData = this.templatesData;
    } else {
      this.filteredTemplatesData = this.templatesData.filter(template =>
        template.label.toLowerCase().includes(term)
      );
    }
  }
  
  addTemplate(): void {
    this.httpService.requestCreateStatisticalTemplate(this.new_template).subscribe({
      next: (response) => {
        this.templatesData.push(response);
        this.filteredTemplatesData = this.templatesData;
        this.new_template = { label: "", data: {} };
      }
    });
  }
}
