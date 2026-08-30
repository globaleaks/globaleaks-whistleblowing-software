/**
 * The metrics a statistical template is composed of.
 *
 * The catalog carries no value: a template says what the statistics present,
 * and the values are read and frozen when a report is saved.
 */
export class metricCatalogResolverModel {
  question_template_dropdown_metrics: Array<{
    id: string;
    template_id: string;
    title: string;
    options: Array<{
      id: string;
      label: string;
    }>;
  }> = [];
}
