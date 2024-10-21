import {AfterViewInit, Component, TemplateRef, ViewChild, ChangeDetectorRef, inject} from "@angular/core";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {Tab} from "@app/models/component-model/tab";
import {AuditLogTab1Component} from "@app/pages/admin/auditlog/auditlog-tab1/audit-log-tab1.component";
import {AuditLogTab2Component} from "@app/pages/admin/auditlog/auditlog-tab2/audit-log-tab2.component";
import {AuditLogTab3Component} from "@app/pages/admin/auditlog/auditlog-tab3/audit-log-tab3.component";
import {AuditLogTab4Component} from "@app/pages/admin/auditlog/auditlog-tab4/audit-log-tab4.component";
import {NgbNav, NgbNavItem, NgbNavItemRole, NgbNavLinkButton, NgbNavLinkBase, NgbNavContent, NgbNavOutlet, NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {NgTemplateOutlet} from "@angular/common";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {TranslateModule} from "@ngx-translate/core";

@Component({
    selector: "src-auditlog",
    templateUrl: "./audit-log.component.html",
    standalone: true,
    imports: [NgbNav, NgbNavItem, NgbNavItemRole, NgbNavLinkButton, NgbNavLinkBase, NgbNavContent, NgTemplateOutlet, NgbNavOutlet, NgbTooltipModule, AuditLogTab1Component, AuditLogTab2Component, AuditLogTab3Component, AuditLogTab4Component, TranslatorPipe, TranslateModule]
})
export class AuditLogComponent implements AfterViewInit {
  private nodeResolver = inject(NodeResolver);
  private authenticationService = inject(AuthenticationService);
  private cdr = inject(ChangeDetectorRef);

  @ViewChild("tab1") tab1!: TemplateRef<AuditLogTab1Component>;
  @ViewChild("tab2") tab2!: TemplateRef<AuditLogTab2Component>;
  @ViewChild("tab3") tab3!: TemplateRef<AuditLogTab3Component>;
  @ViewChild("tab4") tab4!: TemplateRef<AuditLogTab4Component>;

  tabs: Tab[] = [];
  nodeData: NodeResolver;
  active: string;

  ngAfterViewInit(): void {
    setTimeout(() => {
      this.active = "Audit Log";

      this.nodeData = this.nodeResolver;
      this.tabs = [
        {
          id:"audit_log",
          title: "Audit Log",
          component: this.tab1
        },
      ];
      if (this.authenticationService.session.role === "admin") {
        this.tabs = this.tabs.concat([
          {
            id:"users",
            title: "Users",
            component: this.tab2
          },
          {
            id:"reports",
            title: "Reports",
            component: this.tab3
          },
          {
            id:"scheduled_jobs",
            title: "Scheduled jobs",
            component: this.tab4
          }
        ]);
      }

      this.cdr.detectChanges();
    });
  }
}
