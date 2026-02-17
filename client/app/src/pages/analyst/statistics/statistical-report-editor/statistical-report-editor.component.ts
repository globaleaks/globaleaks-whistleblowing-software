import {Component, EventEmitter, Input, OnInit, Output, inject} from "@angular/core";
import {NgForm, FormsModule} from "@angular/forms";
import {NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {UtilsService} from "@app/shared/services/utils.service";
import {HttpService} from "@app/shared/services/http.service";
import {nodeResolverModel} from "@app/models/resolvers/node-resolver-model";
import {DatePipe, NgClass} from "@angular/common";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {FilterPipe} from "@app/shared/pipes/filter.pipe";
import {statisticalReportResolverModel} from "@app/models/resolvers/statistical-report-resolver-model";
import {StatisticalTemplatesResolver} from "@app/shared/resolvers/statistical-templates.resolver";
import {statisticalTemplateResolverModel} from "@app/models/resolvers/statistical-template-resolver-model";

@Component({
    selector: "src-statistical-report-editor",
    templateUrl: "./statistical-report-editor.component.html",
    standalone: true,
    imports: [DatePipe, FormsModule, NgbTooltipModule, NgClass, TranslatorPipe, FilterPipe]
})
export class StatisticalReportEditorComponent implements OnInit {
  private httpService = inject(HttpService);
  protected nodeResolver = inject(NodeResolver);
  private utilsService = inject(UtilsService);

  @Input() reportData: statisticalReportResolverModel;
  @Input() reportsData: statisticalReportResolverModel[];
  @Input() index: number;
  @Input() editReport: NgForm;
  @Output() dataToParent = new EventEmitter<string>();
  editing = false;
  nodeData: nodeResolverModel;
  templatesData: statisticalTemplateResolverModel[] = [];
  private templatesResolver = inject(StatisticalTemplatesResolver);

  ngOnInit(): void {
    this.nodeData = this.nodeResolver.dataModel;
    this.templatesData = this.templatesResolver.dataModel;
  }

  toggleEditing(): void {
    this.editing = !this.editing;
  }

  deleteReport(report: statisticalReportResolverModel): void {
    this.httpService.requestDeleteStatisticalReport(report.id).subscribe({
      next: () => {
        this.dataToParent.emit();
        this.utilsService.deleteResource(this.reportsData, report);
      },
      error: () => {
      }
    });
  }

  saveReport(report: statisticalReportResolverModel) {
    this.httpService.requestUpdateStatisticalReport(report.id, report).subscribe({});
  }

  exportReport(report: statisticalReportResolverModel) {
    this.utilsService.generateCSV('report', [report], ['id', 'name', 'creation_date', 'template_id']);
  }

}
