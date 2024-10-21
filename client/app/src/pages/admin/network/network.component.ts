import { Component, TemplateRef, ViewChild, AfterViewInit, ChangeDetectorRef, inject } from "@angular/core";
import {Tab} from "@app/models/component-model/tab";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {HttpsComponent} from "@app/pages/admin/network/https/https.component";
import {TorComponent} from "@app/pages/admin/network/tor/tor.component";
import {AccessControlComponent} from "@app/pages/admin/network/access-control/access-control.component";
import {UrlRedirectsComponent} from "@app/pages/admin/network/url-redirects/url-redirects.component";
import { NgbNav, NgbNavItem, NgbNavItemRole, NgbNavLinkButton, NgbNavLinkBase, NgbNavContent, NgbNavOutlet } from "@ng-bootstrap/ng-bootstrap";
import { NgTemplateOutlet } from "@angular/common";
import { TranslatorPipe } from "@app/shared/pipes/translate";

@Component({
    selector: "src-network",
    templateUrl: "./network.component.html",
    standalone: true,
    imports: [NgbNav, NgbNavItem, NgbNavItemRole, NgbNavLinkButton, NgbNavLinkBase, NgbNavContent, NgTemplateOutlet, NgbNavOutlet, HttpsComponent, TorComponent, AccessControlComponent, UrlRedirectsComponent, TranslatorPipe]
})
export class NetworkComponent implements AfterViewInit {
  node = inject(NodeResolver);
  private cdr = inject(ChangeDetectorRef);

  @ViewChild("tab1") tab1!: TemplateRef<HttpsComponent>;
  @ViewChild("tab2") tab2!: TemplateRef<TorComponent>;
  @ViewChild("tab3") tab3!: TemplateRef<AccessControlComponent>;
  @ViewChild("tab4") tab4!: TemplateRef<UrlRedirectsComponent>;

  tabs: Tab[];
  nodeData: NodeResolver;
  active: string;

  ngAfterViewInit(): void {
    setTimeout(() => {
      this.active = "HTTPS";

      this.nodeData = this.node;
      this.tabs = [
        {
          id:"https",
          title: "HTTPS",
          component: this.tab1
        },
        {
          id:"tor",
          title: "Tor",
          component: this.tab2
        },
        {
          id:"access_control",
          title: "Access control",
          component: this.tab3
        },
        {
          id:"url_redirects",
          title: "URL redirects",
          component: this.tab4
        },
      ];

      this.cdr.detectChanges();
    });
  }
}