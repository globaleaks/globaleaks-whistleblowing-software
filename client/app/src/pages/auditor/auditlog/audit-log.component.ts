import {Component, inject} from "@angular/core";
import {TabsComponent} from "@app/shared/components/tabs/tabs.component";
import {TabDirective} from "@app/shared/components/tabs/tab.directive";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {AuditLogTab1Component} from "@app/pages/auditor/auditlog/auditlog-tab1/audit-log-tab1.component";
import {AuditLogTab2Component} from "@app/pages/auditor/auditlog/auditlog-tab2/audit-log-tab2.component";
import {AuditLogTab3Component} from "@app/pages/auditor/auditlog/auditlog-tab3/audit-log-tab3.component";
import {AuditLogTab4Component} from "@app/pages/auditor/auditlog/auditlog-tab4/audit-log-tab4.component";

@Component({
    selector: "src-auditlog",
    templateUrl: "./audit-log.component.html",
    standalone: true,
    imports: [TabsComponent, TabDirective, AuditLogTab1Component, AuditLogTab2Component, AuditLogTab3Component, AuditLogTab4Component]
})
export class AuditLogComponent {
  protected isAuditor = inject(AuthenticationService).session.role === "auditor";
}
