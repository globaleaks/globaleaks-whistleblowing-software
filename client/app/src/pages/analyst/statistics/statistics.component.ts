import {Component, OnInit, inject} from '@angular/core';
import {StatisticsResolver} from '@app/shared/resolvers/statistics.resolver';
import {TranslateService, TranslateModule} from '@ngx-translate/core';

import {BaseChartDirective, provideCharts, withDefaultRegisterables} from 'ng2-charts';
import {TranslatorPipe} from '@app/shared/pipes/translate';

@Component({
    selector: 'src-statistics',
    templateUrl: './statistics.component.html',
    standalone: true,
    imports: [
    BaseChartDirective,
    TranslateModule,
    TranslatorPipe
],
    providers: [provideCharts(withDefaultRegisterables())],
})
export class StatisticsComponent implements OnInit {
  private translateService = inject(TranslateService);
  private statisticsResolver = inject(StatisticsResolver);

  charts: any[] = [];

  ngOnInit(): void {
    this.initializeCharts();
  }

  private calculatePercentage(value: number, total: number): string {
    if (total === 0) {
      return '0.0';
    }
    return ((value / total) * 100).toFixed(1);
  }

  private createChart(title: string, labels: string[], values: number[], colors: string[]) {
    let total = 0;
    let i: any;

    for (i in values) {
      total += values[i];
    }

    for (i in labels) {
      labels[i] = this.translateService.instant(labels[i]) + ": " + this.calculatePercentage(values[i], total) + "%";
    }

    return {
      title: this.translateService.instant(title),
      labels: labels,
      datasets: [{'labels': labels, 'data': values, 'backgroundColor': colors}],
    };
  }

  private initializeCharts(): void {
    const { dataModel } = this.statisticsResolver;
    const reports_count: number = dataModel.reports_count;

    const a_1: number = dataModel.reports_with_no_access || 0;
    const a_2: number = reports_count - dataModel.reports_with_no_access || 0;

    const b_1: number = dataModel.reports_anonymous || 0;
    const b_2: number = dataModel.reports_subscribed || 0;
    const b_3: number = dataModel.reports_initially_anonymous || 0;

    const c_1: number = dataModel.reports_tor || 0;
    const c_2: number = reports_count - dataModel.reports_tor || 0;

    const d_1: number = dataModel.reports_mobile || 0;
    const d_2: number = reports_count - dataModel.reports_mobile || 0;

    this.charts.push(this.createChart("Returning whistleblowers", ["Yes", "No"], [a_1, a_2], ["rgb(96,186,255)", "rgb(0,127,224)"]));
    this.charts.push(this.createChart("Anonymity", ["Anonymous", "Subscribed", "Subscribed later"], [b_1, b_2, b_3], ["rgb(96,186,255)", "rgb(0,127,224)", "rgb(0,46,82)"]));
    this.charts.push(this.createChart("Tor", ["Yes", "No"], [c_1, c_2], ["rgb(96,186,255)", "rgb(0,127,224)"]));
    this.charts.push(this.createChart("Mobile", ["Yes", "No"], [d_1, d_2], ["rgb(96,186,255)", "rgb(0,127,224)"]));
  }
}
