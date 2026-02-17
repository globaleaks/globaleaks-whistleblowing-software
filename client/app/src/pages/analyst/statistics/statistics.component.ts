import {ChangeDetectorRef, Component, OnInit, TemplateRef, ViewChild, inject} from '@angular/core';
import {BaseChartDirective, provideCharts, withDefaultRegisterables} from 'ng2-charts';
import {TranslatorPipe} from '@app/shared/pipes/translate';
import {Tab} from '@app/models/component-model/tab';
import {NodeResolver} from '@app/shared/resolvers/node.resolver';
import {FormsModule} from '@angular/forms';
import {NgTemplateOutlet} from '@angular/common';
import {NgbNav, NgbNavItem, NgbNavItemRole, NgbNavLinkButton, NgbNavLinkBase, NgbNavContent, NgbNavOutlet } from '@ng-bootstrap/ng-bootstrap';
import {StatisticalReportsTabComponent} from '@app/pages/analyst/statistics/statistical-reports-tab/statistical-reports-tab.component';
import {StatisticalTemplatesTabComponent} from '@app/pages/analyst/statistics/statistical-templates-tab/statistical-templates-tab.component';

@Component({
    selector: 'src-statistics',
    templateUrl: './statistics.component.html',
    standalone: true,
    imports: [BaseChartDirective, FormsModule, NgbNav, NgbNavItem, NgbNavItemRole, NgbNavLinkButton, NgbNavLinkBase, NgbNavContent, NgTemplateOutlet, NgbNavOutlet, StatisticalReportsTabComponent, StatisticalTemplatesTabComponent, TranslatorPipe],
    providers: [provideCharts(withDefaultRegisterables())],
})
export class StatisticsComponent {
  protected node = inject(NodeResolver);
  private cdr = inject(ChangeDetectorRef);

  @ViewChild("tab1") tab1!: TemplateRef<StatisticalReportsTabComponent>;
  @ViewChild("tab2") tab2!: TemplateRef<StatisticalTemplatesTabComponent>;

  tabs: Tab[];
  nodeData: NodeResolver;
  active: string;

  ngAfterViewInit(): void {
    setTimeout(() => {
      this.active = "Statistical Reports";

      this.nodeData = this.node;
      this.tabs = [
        {
          id:"satistical_reports",
          title: "Statistical Reports",
          component: this.tab1
        },
        {
          id:"templates",
          title: "Templates",
          component: this.tab2
        },
      ];

      this.cdr.detectChanges();
    });
  }
}
