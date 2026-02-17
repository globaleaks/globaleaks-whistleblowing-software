import {Component, Input, OnInit, inject} from "@angular/core";
import {NgForm, FormsModule} from "@angular/forms";
import {Constants} from "@app/shared/constants/constants";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {HttpService} from "@app/shared/services/http.service";
import {NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {NgClass} from "@angular/common";
import {StatisticalReportsResolver} from "@app/shared/resolvers/statistical-reports.resolver";
import {StatisticalTemplatesResolver} from "@app/shared/resolvers/statistical-templates.resolver";
import {statisticalReportResolverModel} from "@app/models/resolvers/statistical-report-resolver-model";
import {statisticalTemplateResolverModel} from "@app/models/resolvers/statistical-template-resolver-model";
import {StatisticalReportEditorComponent} from "@app/pages/analyst/statistics/statistical-report-editor/statistical-report-editor.component";

@Component({
    selector: "src-statistical-reports-tab",
    templateUrl: "./statistical-reports-tab.component.html",
    standalone: true,
    imports: [StatisticalReportEditorComponent, FormsModule, NgbTooltipModule, NgClass, TranslatorPipe]
})
export class StatisticalReportsTabComponent implements OnInit {
  protected nodeResolver = inject(NodeResolver);
  private httpService = inject(HttpService);
  private reportsResolver = inject(StatisticalReportsResolver);
  private templatesResolver = inject(StatisticalTemplatesResolver);
  @Input() statisticsForm: NgForm;
  
  reportsData: statisticalReportResolverModel[] = [];
  templatesData: statisticalTemplateResolverModel[] = [];
  @Input() reportsForm: NgForm;
  showAddReport = false;
  new_report: { label: string; template_id: string; data: any } = {
    label: "",
    template_id: "",
    data: {}
  };

  protected readonly Constants = Constants;

  ngOnInit(): void {
    this.reportsData = this.reportsResolver.dataModel;
    this.templatesData = this.templatesResolver.dataModel;
  }

  toggleAddReport() {
    this.showAddReport = !this.showAddReport;
  }

  addReport() {
    this.httpService.requestCreateStatisticalReport(this.new_report as any).subscribe({
      next: (response) => {
        this.reportsData.push(response);
        this.new_report = { label: "", template_id: "", data: {} };
      }
    });
  }
}

