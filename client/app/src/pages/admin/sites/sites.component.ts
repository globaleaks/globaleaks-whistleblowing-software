import {Component, TemplateRef, ViewChild, AfterViewInit, ChangeDetectorRef} from "@angular/core";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {Tab} from "@app/models/component-model/tab";
import {SitesTab1Component} from "@app/pages/admin/sites/sites-tab1/sites-tab1.component";
import {SitesTab2Component} from "@app/pages/admin/sites/sites-tab2/sites-tab2.component";

@Component({
  selector: "src-sites",
  templateUrl: "./sites.component.html"
})
export class SitesComponent implements AfterViewInit {
  @ViewChild("tab1") tab1!: TemplateRef<SitesTab1Component>;
  @ViewChild("tab2") tab2!: TemplateRef<SitesTab2Component>;

  tabs: Tab[];
  nodeData: NodeResolver;
  active: string;

  constructor(public node: NodeResolver, public authenticationService: AuthenticationService, private cdr: ChangeDetectorRef) {
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