import {Component, computed, inject, ChangeDetectionStrategy} from "@angular/core";
import {JobResolver} from "@app/shared/resolvers/job.resolver";
import {UtilsService} from "@app/shared/services/utils.service";
import {DatePipe} from "@angular/common";
import {TranslateModule} from "@ngx-translate/core";
import {PaginatedInterfaceComponent} from "@app/shared/components/paginated-interface/paginated-interface.component";


@Component({
    changeDetection: ChangeDetectionStrategy.OnPush,
    selector: "src-auditlog-tab4",
    templateUrl: "./audit-log-tab4.component.html",
    standalone: true,
    imports: [DatePipe, PaginatedInterfaceComponent, TranslateModule]
})
export class AuditLogTab4Component {
  private readonly utilsService = inject(UtilsService);
  private readonly jobResolver = inject(JobResolver);

  readonly jobs = computed(() => this.jobResolver.resource.value());

  exportAuditLog() {
    this.utilsService.generateCSV('jobs', this.jobs());
  }
}
