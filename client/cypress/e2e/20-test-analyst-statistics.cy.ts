import {t} from "../support/i18n";
describe("Analyst statistics templates and reports", () => {

  const openTemplatesTab = (): void => {
    cy.get('[data-cy="templates"]').click();
    cy.waitForPageIdle();
  };

  const openReportsTab = (): void => {
    cy.get('[data-cy="statistical_reports"]').click();
    cy.waitForPageIdle();
  };

  const createTemplate = (label: string): void => {
    openTemplatesTab();
    cy.get(".show-add-template-btn").click();
    cy.get("#new-template-label").clear().type(label);
    cy.get(".addTemplate #add-btn").click();
    cy.waitForPageIdle();
    cy.contains(".templateList .config-item", label).should("be.visible");
  };

  // Metrics are added from the modal of the card closing the grid, each with its representation
  const addMetric = (title: string, displayType: string): void => {
    cy.get(".add-metric-card").first().click();
    cy.get("#metric-select").click();
    cy.get(".ng-dropdown-panel .ng-option").contains(title).click();
    cy.get(`[data-cy="display-type-${displayType}"]`).click();
    cy.get("#modal-action-ok").should("not.be.disabled").click();
    cy.waitForPageIdle();
  };

  const openTemplateEditor = (label: string): void => {
    cy.contains(".templateList .config-item", label)
      .within(() => {
        cy.get("#edit_template").click();
      });
    cy.waitForPageIdle();
  };

  const createReport = (label: string, template: string): void => {
    openReportsTab();
    cy.get(".show-add-report-btn").click();
    cy.get("#new-report-label").type(label);
    cy.get("#new-report-template-id option")
      .contains(template)
      .invoke("attr", "value")
      .then((value) => {
        cy.get("#new-report-template-id").select(value as string);
      });
    cy.get(".addReport #add-btn").should("not.be.disabled").click();
    cy.waitForPageIdle();
  };

  beforeEach(() => {
    cy.login_analyst();
    cy.visit("/#/analyst/statistics");
    cy.waitForPageIdle();
  });

  afterEach(() => {
    cy.logout();
  });

  // the analyst creates and modifies the templates of the reports.
  it("creates, searches, edits and deletes a statistical template", () => {

    createTemplate("Template");

    cy.takeScreenshot("analyst/statistics_templates");

    cy.get(`input[placeholder*='${t("Search")}']`).type("Template");
    cy.contains(".templateList .config-item", "Template").should("be.visible");
    cy.get(`input[placeholder*='${t("Search")}']`).clear();

    cy.contains(".templateList .config-item", "Template")
      .within(() => {
        cy.get("#edit_template").click();
      });

    cy.get("input[name='label']").first().clear().type("Updated Template");
    cy.get("#save_template").first().click();
    cy.waitForPageIdle();

    cy.contains(".templateList .config-item", "Updated Template").should("be.visible");

    cy.contains(".templateList .config-item", "Updated Template")
      .within(() => {
        cy.get("#delete_template").click();
      });
    cy.waitForPageIdle();

    cy.contains(".templateList .config-item", "Updated Template").should("not.exist");
  });

  // A template is a preset like a site profile: composed, exported and imported here
  it("carries a statistical template out as a file and puts it back", () => {
    const label = "Model template";
    const exported = `cypress/downloads/${label}.json`;

    createTemplate(label);
    openTemplateEditor(label);
    addMetric(t("Average time to opening"), "number");
    cy.get("#save_template").first().click();
    cy.waitForPageIdle();

    cy.contains(".templateList .config-item", label).within(() => {
      cy.get("[data-action='export']").click();
    });

    // the export holds the template as composed
    cy.readFile(exported, {timeout: 20000}).then((carried: any) => {
      expect(carried.label).to.eq(label);
      expect(carried.data).to.be.an("object");
    });

    cy.contains(".templateList .config-item", label).within(() => {
      cy.get("#delete_template").click();
    });
    cy.waitForPageIdle();
    cy.contains(".templateList .config-item", label).should("not.exist");

    // the file input is hidden behind its label
    cy.get("#import-template-file").selectFile(exported, {force: true});
    cy.contains(".templateList .config-item", label).should("be.visible");

    // leave nothing behind
    cy.contains(".templateList .config-item", label).within(() => {
      cy.get("#delete_template").click();
    });
    cy.waitForPageIdle();
    cy.contains(".templateList .config-item", label).should("not.exist");
  });

  // the analyst generates, saves, consults and deletes the reports.
  it("validates required fields, creates, edits and deletes a statistical report", () => {

    createTemplate("Report Template");
    openReportsTab();

    cy.get(".show-add-report-btn").click();
    cy.get(".addReport #add-btn").should("be.disabled");

    cy.get("#new-report-label").type("Report");
    cy.get(".addReport #add-btn").should("be.disabled");

    cy.get("#new-report-template-id option")
      .contains("Report Template")
      .invoke("attr", "value")
      .then((value) => {
        expect(value, "template option value").to.not.be.undefined;
        cy.get("#new-report-template-id").select(value as string);
      });

    cy.get(".addReport #add-btn").should("not.be.disabled").click();
    cy.waitForPageIdle();

    cy.takeScreenshot("analyst/statistics_reports");

    // a saved report renders the template it was generated from; the label is fixed at creation
    cy.contains("tr.reportList", "Report")
      .within(() => {
        cy.get("#edit_report").click();
      });
    cy.waitForPageIdle();
    // a template with no metrics has no height: assert that the report opens
    cy.get('[data-cy="statistical-report-details"]').should("be.visible");
    cy.get("src-statistical-template-view").should("exist");

    cy.contains("tr.reportList", "Report")
      .within(() => {
        cy.get("#delete_report").click();
      });
    cy.waitForPageIdle();

    cy.contains("tr.reportList", "Report").should("not.exist");
  });

  it("configures the timing metrics and the representation of each metric", () => {
    createTemplate("Timing Template");
    openTemplateEditor("Timing Template");

    cy.takeScreenshot("analyst/statistics_template_editor");

    addMetric(t("Average time to opening"), "number");
    addMetric(t("Average time to first reply"), "number");
    addMetric(t("Average time to closure"), "number");

    // a distribution metric admits a diagram: the representation is chosen where more than one
    // applies
    cy.get(".add-metric-card").first().click();
    cy.get("#metric-select").click();
    cy.get(".ng-dropdown-panel .ng-option").contains(t("Anonymity")).click();
    cy.takeScreenshot("analyst/statistics_add_metric_detail", ".modal-dialog");
    cy.takeScreenshot("analyst/statistics_chart_type_detail", ".display-section");
    cy.get('[data-cy="display-type-pie"]').click();
    cy.get("#modal-action-ok").should("not.be.disabled").click();
    cy.waitForPageIdle();

    cy.get("#save_template").first().click();
    cy.waitForPageIdle();

    openTemplateEditor("Timing Template");
    cy.contains("#Content", t("Average time to opening")).should("be.visible");
    cy.contains("#Content", t("Average time to first reply")).should("be.visible");
    cy.contains("#Content", t("Average time to closure")).should("be.visible");
    cy.takeScreenshot("analyst/statistics_timing_metrics");
    cy.takeScreenshot("analyst/statistics_timing_metrics_detail", ".metrics-section");
    cy.takeScreenshot("analyst/statistics_closure_metric_detail", ".metric-card:eq(2)");
    cy.takeScreenshot("analyst/statistics_chart_types", ".chart-card:first");
  });

  // The export opens the print window: what is asserted is the printable rendition
  it("exports a report through the print window of the browser", () => {
    createReport("Export Report", "Timing Template");

    cy.contains("tr.reportList", "Export Report")
      .within(() => {
        cy.get("#edit_report").click();
      });
    cy.waitForPageIdle();

    cy.takeScreenshot("analyst/statistics_report_export");
    cy.takeScreenshot("analyst/statistics_report_actions_detail", '[data-cy="statistical-report-0"]');
    cy.takeScreenshot("analyst/statistics_closure_metric");

    cy.window().then((win: any) => {
      cy.stub(win, "print").as("browserPrint");
    });

    cy.get(".downloadButton").click();

    // the printable rendition is appended and the browser is asked to print it
    cy.get(".report-print-container").should("exist");
    cy.takeScreenshot("analyst/statistics_report_print_detail", ".report-print-container");
    cy.get("@browserPrint").should("have.been.called");
  });

  // the analyst restricts a report to the channels it wants to observe.
  it("filters a report by channel", () => {
    openReportsTab();

    // the filters live in the form that creates the report
    cy.get(".show-add-report-btn").click();
    cy.get("#new-report-label").clear().type("Channel Report");
    cy.get("#new-report-template-id option")
      .contains("Timing Template")
      .invoke("attr", "value")
      .then((value) => {
        cy.get("#new-report-template-id").select(value as string);
      });

    cy.takeScreenshot("analyst/statistics_channel_filter");

    cy.get("#ReportObservationFilter .dropdown-multi-select-container button").click();
    cy.get("ng-multiselect-dropdown .multiselect-item-checkbox").should("be.visible");
    cy.takeScreenshot("analyst/statistics_channel_filter_detail", ".addReport");
    cy.get("ng-multiselect-dropdown .multiselect-item-checkbox").first().click();
    cy.waitForPageIdle();

    cy.get('[data-cy="filter_clear_button"]').should("be.visible");
    cy.get("#ReportObservationFilter .badge").should("be.visible");

    cy.get(".addReport #add-btn").should("not.be.disabled").click();
    cy.waitForPageIdle();

    cy.contains("tr.reportList", "Channel Report")
      .within(() => {
        cy.get("#edit_report").click();
      });
    cy.waitForPageIdle();
    cy.get("#StatisticsObservation").should("be.visible");
    cy.takeScreenshot("analyst/statistics_report_channels_detail", ".reportDetail");
  });

  // the analyst restricts a report to a range of dates.
  it("filters a report by date range", () => {
    openReportsTab();

    cy.get(".show-add-report-btn").click();

    cy.get('[data-cy="filter_date_button"]').click();
    cy.get("#ReportObservationFilter src-date-selector .ngb-dp-day").should("be.visible");
    cy.takeScreenshot("analyst/statistics_date_filter");
    cy.takeScreenshot("analyst/statistics_date_filter_detail", "#ReportObservationFilter src-date-selector");

    // the range is two clicks; the day cells come from a custom template of the picker
    cy.get("#ReportObservationFilter src-date-selector .custom-date-selector").should("have.length.greaterThan", 1);
    cy.get("#ReportObservationFilter src-date-selector .custom-date-selector").first().click();
    cy.get("#ReportObservationFilter src-date-selector .custom-date-selector").last().click();
    cy.waitForPageIdle();

    cy.get('[data-cy="filter_clear_button"]').should("be.visible");
    cy.get('[data-cy="filter_date_button"]').should("have.class", "filter-active");

    cy.get('[data-cy="filter_clear_button"]').click();
    cy.waitForPageIdle();
  });

});
