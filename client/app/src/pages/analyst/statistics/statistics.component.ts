import {Component, computed, inject} from '@angular/core';
import {FormsModule} from '@angular/forms';
import {AuthenticationService} from '@app/services/helper/authentication.service';
import {PreferenceResolver} from '@app/shared/resolvers/preference.resolver';
import {StatisticsResolver} from '@app/shared/resolvers/statistics.resolver';
import {StatisticalTemplatesResolver} from '@app/shared/resolvers/statistical-templates.resolver';
import {statisticalTemplateResolverModel} from '@app/models/resolvers/statistical-template-resolver-model';
import {TranslateModule} from '@ngx-translate/core';
import {TabsComponent} from '@app/shared/components/tabs/tabs.component';
import {TabDirective} from '@app/shared/components/tabs/tab.directive';
import {StatisticalReportsTabComponent} from '@app/pages/analyst/statistics/statistical-reports-tab/statistical-reports-tab.component';
import {StatisticalTemplatesTabComponent} from '@app/pages/analyst/statistics/statistical-templates-tab/statistical-templates-tab.component';
import {StatisticalTemplateViewComponent} from '@app/pages/analyst/statistics/statistical-template-view/statistical-template-view.component';

/**
 * The statistics of a site.
 *
 * The analysts read the statistics and compose the reports; whoever holds the
 * permission composes the templates the statistics and the reports are
 * presented with, administrators included: to them the page offers the
 * templates alone.
 */
@Component({
    selector: 'src-statistics',
    templateUrl: './statistics.component.html',
    standalone: true,
    imports: [
    FormsModule,
    TabsComponent,
    TabDirective,
    StatisticalReportsTabComponent,
    StatisticalTemplatesTabComponent,
    StatisticalTemplateViewComponent,
    TranslateModule
],
})
export class StatisticsComponent {
  private readonly statisticsResolver = inject(StatisticsResolver);
  private readonly templatesResolver = inject(StatisticalTemplatesResolver);
  private readonly preferenceResolver = inject(PreferenceResolver);
  private readonly authenticationService = inject(AuthenticationService);

  /** The statistics of the platform, as they stand right now. */
  readonly statistics = computed(() => this.statisticsResolver.resource.value());

  get templatesData(): statisticalTemplateResolverModel[] {
    return this.templatesResolver.dataModel;
  }

  /** The template the statistics are presented with, configured by the administrators. */
  get defaultTemplate(): statisticalTemplateResolverModel | null {
    return this.templatesData?.find(template => template.default) || this.templatesData?.[0] || null;
  }

  get isAnalyst(): boolean {
    return this.authenticationService.session?.role === "analyst";
  }

  get canConfigureTemplates(): boolean {
    return !!this.preferenceResolver.dataModel?.profile?.permissions?.can_configure_statistical_report_templates;
  }
}
