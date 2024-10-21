import {AfterViewInit, Component, TemplateRef, ViewChild} from "@angular/core";
import {Tab} from "@app/models/component-model/tab";
import {Tab1Component} from "@app/pages/admin/settings/tab1/tab1.component";
import { FormsModule } from "@angular/forms";
import { NgbNav, NgbNavItem, NgbNavItemRole, NgbNavLinkButton, NgbNavLinkBase, NgbNavContent, NgbNavOutlet } from "@ng-bootstrap/ng-bootstrap";
import { NgTemplateOutlet } from "@angular/common";
import { TranslateModule } from "@ngx-translate/core";
import { TranslatorPipe } from "@app/shared/pipes/translate";

@Component({
    selector: "src-custodian-settings",
    templateUrl: "./settings.component.html",
    standalone: true,
    imports: [FormsModule, NgbNav, NgbNavItem, NgbNavItemRole, NgbNavLinkButton, NgbNavLinkBase, NgbNavContent, NgTemplateOutlet, NgbNavOutlet, Tab1Component, TranslateModule, TranslatorPipe]
})
export class CustodianSettingsComponent implements AfterViewInit {
  @ViewChild("tab1") tab1!: TemplateRef<Tab1Component>;
  tabs: Tab[];
  active: string;

  ngAfterViewInit(): void {
    this.active = "Settings";

    this.tabs = [
      {
        title: "Settings",
        component: this.tab1
      },
    ];
  }
}
