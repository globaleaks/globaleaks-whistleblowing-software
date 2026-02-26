import {Component, Input, OnInit, inject} from "@angular/core";
import {NgForm, FormsModule} from "@angular/forms";
import {Constants} from "@app/shared/constants/constants";
import {HttpService} from "@app/shared/services/http.service";
import {NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {NgClass} from "@angular/common";
import {StatisticalReportsResolver} from "@app/shared/resolvers/statistical-reports.resolver";
import {StatisticalTemplatesResolver} from "@app/shared/resolvers/statistical-templates.resolver";
import {statisticalReportResolverModel} from "@app/models/resolvers/statistical-report-resolver-model";
import {FilterOption, FilterOptionsResponse, statisticalTemplateResolverModel} from "@app/models/resolvers/statistical-template-resolver-model";
import {StatisticalReportEditorComponent} from "@app/pages/analyst/statistics/statistical-report-editor/statistical-report-editor.component";

@Component({
    selector: "src-statistical-reports-tab",
    templateUrl: "./statistical-reports-tab.component.html",
    standalone: true,
    imports: [StatisticalReportEditorComponent, FormsModule, NgbTooltipModule, NgClass, TranslatorPipe]
})
export class StatisticalReportsTabComponent implements OnInit {
  private readonly httpService = inject(HttpService);
  private readonly reportsResolver = inject(StatisticalReportsResolver);
  private readonly templatesResolver = inject(StatisticalTemplatesResolver);
  @Input() statisticsForm!: NgForm;
  @Input() filterOptions: FilterOptionsResponse;
  
  reportsData: statisticalReportResolverModel[] = [];
  @Input() reportsForm!: NgForm;
  showAddReport = false;
  new_report: { label: string; template_id: string; data: Record<string, unknown> } = {
    label: "",
    template_id: "",
    data: {}
  };

  protected readonly Constants = Constants;
  get templatesData(): statisticalTemplateResolverModel[] {
    return this.templatesResolver.dataModel;
  }

  ngOnInit(): void {
    this.reportsData = this.reportsResolver.dataModel;
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

  toggleAddReport(): void {
    this.showAddReport = !this.showAddReport;
  }

  addReport(): void {
    this.httpService.requestCreateStatisticalReport(this.new_report).subscribe({
      next: (response) => {
        this.reportsData.push(response);
        this.new_report = { label: "", template_id: "", data: {} };
      }
    });
  }
}
