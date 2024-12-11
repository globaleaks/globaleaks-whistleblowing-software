import {Component, TemplateRef, ViewChild, OnInit, AfterViewInit, ChangeDetectorRef, inject} from "@angular/core";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {Tab} from "@app/models/component-model/tab";
import {SitesTab1Component} from "@app/pages/admin/sites/sites-tab1/sites-tab1.component";
import {SitesTab2Component} from "@app/pages/admin/sites/sites-tab2/sites-tab2.component";
import {SitesTab3Component} from "@app/pages/admin/sites/sites-tab3/sites-tab3.component";
import {FormsModule} from "@angular/forms";
import {NgbNav, NgbNavItem, NgbNavItemRole, NgbNavLinkButton, NgbNavLinkBase, NgbNavContent, NgbNavOutlet} from "@ng-bootstrap/ng-bootstrap";
import {NgTemplateOutlet} from "@angular/common";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {TranslateModule} from "@ngx-translate/core";

@Component({
    selector: "src-sites",
    templateUrl: "./sites.component.html",
    standalone: true,
    imports: [FormsModule, NgbNav, NgbNavItem, NgbNavItemRole, NgbNavLinkButton, NgbNavLinkBase, NgbNavContent, NgTemplateOutlet, NgbNavOutlet, SitesTab1Component, SitesTab2Component, SitesTab3Component, TranslatorPipe, TranslateModule]
})
export class SitesComponent implements OnInit, AfterViewInit {
  node = inject(NodeResolver);
  authenticationService = inject(AuthenticationService);
  private cdr = inject(ChangeDetectorRef);

  @ViewChild("tab1") tab1!: TemplateRef<SitesTab1Component>;
  @ViewChild("tab2") tab2!: TemplateRef<SitesTab2Component>;
  @ViewChild("tab3") tab3!: TemplateRef<SitesTab3Component>;

  tabs: Tab[];
  nodeData: NodeResolver;
  active: string;

  ngOnInit() {
  }

  ngAfterViewInit(): void {
    setTimeout(() => {
      this.active = "Sites";

      this.nodeData = this.node;
      this.tabs = [
        {
          id:"sites",
          title: "Sites",
          component: this.tab1
        },
        {
          id:"profiles",
          title: "Profiles",
          component: this.tab3
        },
      ];
      if (this.authenticationService.session.role === "admin") {
        this.tabs = this.tabs.concat([
          {
            id:"options",
            title: "Options",
            component: this.tab2
          }
        ]);
      }

      this.cdr.detectChanges();
    });
  }
}