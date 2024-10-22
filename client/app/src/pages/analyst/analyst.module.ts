import {NgModule} from "@angular/core";
import {CommonModule} from "@angular/common";
import {RouterModule} from "@angular/router";
import {TranslateModule} from "@ngx-translate/core";
import {SharedModule} from "@app/shared.module";
import {FormsModule} from "@angular/forms";
import {NgbDatepickerModule, NgbDropdownModule, NgbModule, NgbNavModule} from "@ng-bootstrap/ng-bootstrap";
import {NgMultiSelectDropDownModule} from "ng-multiselect-dropdown";
import { HomeComponent } from '@app/pages/analyst/home/home.component';
import { SidebarComponent } from '@app/pages/analyst/sidebar/sidebar.component';
import { StatisticsComponent } from '@app/pages/analyst/statistics/statistics.component';
import { BaseChartDirective, provideCharts, withDefaultRegisterables } from 'ng2-charts';
import { ReportsComponent } from "@app/pages/analyst/reports/reports.component";

@NgModule({
  declarations:[
    HomeComponent,
    SidebarComponent,
    StatisticsComponent,
    ReportsComponent
  ],
  imports: [
    CommonModule, RouterModule, TranslateModule, SharedModule, FormsModule,
    NgbModule, NgbNavModule,BaseChartDirective,
    NgbDatepickerModule, NgbDropdownModule, NgMultiSelectDropDownModule.forRoot()

  ],
  providers: [provideCharts(withDefaultRegisterables())],
  exports: [SidebarComponent]
})
export class AnalystModule { }
