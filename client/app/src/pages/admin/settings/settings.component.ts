import { Component, TemplateRef, ViewChild, AfterViewInit, ChangeDetectorRef, inject } from "@angular/core";
import {NodeResolver} from "app/src/shared/resolvers/node.resolver";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {Tab} from "@app/models/component-model/tab";
import {Tab1Component} from "@app/pages/admin/settings/tab1/tab1.component";
import {Tab2Component} from "@app/pages/admin/settings/tab2/tab2.component";
import {Tab3Component} from "@app/pages/admin/settings/tab3/tab3.component";
import {Tab4Component} from "@app/pages/admin/settings/tab4/tab4.component";
import {Tab5Component} from "@app/pages/admin/settings/tab5/tab5.component";
import { FormsModule } from "@angular/forms";
import { NgbNav, NgbNavItem, NgbNavItemRole, NgbNavLinkButton, NgbNavLinkBase, NgbNavContent, NgbNavOutlet } from "@ng-bootstrap/ng-bootstrap";
import { NgTemplateOutlet } from "@angular/common";
import { TranslatorPipe } from "@app/shared/pipes/translate";
import { TranslateModule } from "@ngx-translate/core";

@Component({
    selector: "src-admin-settings",
    templateUrl: "./settings.component.html",
    standalone: true,
    imports: [FormsModule, NgbNav, NgbNavItem, NgbNavItemRole, NgbNavLinkButton, NgbNavLinkBase, NgbNavContent, NgTemplateOutlet, NgbNavOutlet, Tab1Component, Tab2Component, Tab3Component, Tab4Component, Tab5Component, TranslatorPipe, TranslateModule]
})
export class AdminSettingsComponent implements AfterViewInit {
  protected node = inject(NodeResolver);
  protected authenticationService = inject(AuthenticationService);
  private cdr = inject(ChangeDetectorRef);

  @ViewChild("tab1") tab1!: TemplateRef<Tab1Component>;
  @ViewChild("tab2") tab2!: TemplateRef<Tab2Component>;
  @ViewChild("tab3") tab3!: TemplateRef<Tab3Component>;
  @ViewChild("tab4") tab4!: TemplateRef<Tab4Component>;
  @ViewChild("tab5") tab5!: TemplateRef<Tab5Component>;
  tabs: Tab[];
  nodeData: NodeResolver;
  active: string;

  ngAfterViewInit(): void {
    setTimeout(() => {
      this.active = "Settings";

      this.nodeData = this.node;
      this.tabs = [
        {
          id:"settings",
          title: "Settings",
          component: this.tab1
        },
      ];
      if (this.authenticationService.session.role === "admin") {
        this.tabs = this.tabs.concat([
          {
            id:"files",
            title: "Files",
            component: this.tab2
          },
          {
            id:"languages",
            title: "Languages",
            component: this.tab3
          },
          {
            id:"text_customization",
            title: "Text customization",
            component: this.tab4
          },
          {
            id:"advanced",
            title: "Advanced",
            component: this.tab5
          }
        ]);
      }

      this.cdr.detectChanges();
    });
  }
}