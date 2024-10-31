import {Component, OnInit, inject} from "@angular/core";
import {JobResolver} from "@app/shared/resolvers/job.resolver";
import {jobResolverModel} from "@app/models/resolvers/job-resolver-model";
import {UtilsService} from "@app/shared/services/utils.service";
import {DatePipe} from "@angular/common";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {TranslateModule} from "@ngx-translate/core";

@Component({
    selector: "src-auditlog-tab4",
    templateUrl: "./audit-log-tab4.component.html",
    standalone: true,
    imports: [DatePipe, TranslatorPipe, TranslateModule]
})
export class AuditLogTab4Component implements OnInit{
  private utilsService = inject(UtilsService);
  private jobResolver = inject(JobResolver);

  currentPage = 1;
  pageSize = 20;
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

  getPaginatedData(): jobResolverModel[] {
    const startIndex = (this.currentPage - 1) * this.pageSize;
    const endIndex = startIndex + this.pageSize;
    return this.jobs.slice(startIndex, endIndex);
  }

  exportAuditLog() {
    this.utilsService.generateCSV(JSON.stringify(this.jobs), 'jobs', []);
  }
}
