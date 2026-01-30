import {Component, OnInit, inject} from "@angular/core";
import {JobResolver} from "@app/shared/resolvers/job.resolver";
import {jobResolverModel} from "@app/models/resolvers/job-resolver-model";
import {UtilsService} from "@app/shared/services/utils.service";
import {DatePipe} from "@angular/common";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {TranslateModule} from "@ngx-translate/core";
import {PaginatedInterfaceComponent} from "@app/shared/components/paginated-interface/paginated-interface.component";


@Component({
    selector: "src-auditlog-tab4",
    templateUrl: "./audit-log-tab4.component.html",
    standalone: true,
    imports: [DatePipe, PaginatedInterfaceComponent, TranslatorPipe, TranslateModule]
})
export class AuditLogTab4Component implements OnInit{
  private utilsService = inject(UtilsService);
  private jobResolver = inject(JobResolver);

  jobs: jobResolverModel[] = [];

  ngOnInit() {
    this.loadAuditLogData();
  }

  loadAuditLogData() {
    if (Array.isArray(this.jobResolver.dataModel)) {
      this.jobs = this.jobResolver.dataModel;
    } else {
      this.jobs = [this.jobResolver.dataModel];
    }
  }

  exportAuditLog() {
    this.utilsService.generateCSV('jobs', this.jobs);
  }
}
