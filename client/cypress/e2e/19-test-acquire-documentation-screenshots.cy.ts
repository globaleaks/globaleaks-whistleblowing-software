describe("acquire screenshots necessary for user documentation - Admin Section", () => {
  beforeEach(() => {
    cy.login_admin();
  });

  it("should capture screenshots of the admin section", () => {
    // Home section
    cy.get("#admin_home").first().click();
    cy.takeScreenshot("admin/home");

    cy.get('[data-cy="changelog"]').first().click();
    cy.takeScreenshot("admin/changelog");

    cy.get('[data-cy="license"]').first().click();
    cy.takeScreenshot("admin/license");

    cy.get("#admin_settings").first().click();
    cy.takeScreenshot("admin/site_settings_main_configuration");
    cy.takeScreenshot("admin/site_settings_logo_detail", "#Content");

    cy.get('[data-cy="files"]').first().click();
    cy.takeScreenshot("admin/site_settings_files");

    cy.get('[data-cy="languages"]').first().click();
    cy.takeScreenshot("admin/site_settings_languages");
    cy.takeScreenshot("admin/site_settings_languages_detail", "#Content");

    cy.get('[data-cy="text_customization"]').first().click();
    cy.takeScreenshot("admin/site_settings_text_customization");

    cy.get('[data-cy="advanced"]').first().click();
    cy.takeScreenshot("admin/advanced_settings");

    cy.get("#admin_users").first().click();
    cy.takeScreenshot("admin/users");
    cy.get('[data-cy="options"]').first().click();
    cy.takeScreenshot("admin/users_options");

    cy.get("#admin_questionnaires").first().click();
    cy.takeScreenshot("admin/questionnaires");

    cy.get('[data-cy="question_templates"]').first().click();
    cy.takeScreenshot("admin/question_templates");

    cy.get("#admin_channels").first().click();
    cy.takeScreenshot("admin/channels");

    cy.get("#admin_case_management").first().click();
    cy.takeScreenshot("admin/report_statuses");

    cy.get("#admin_notifications").first().click();
    cy.takeScreenshot("admin/notification_settings");
    cy.takeScreenshot("admin/notification_settings_detail", "#Content");
    cy.get('[data-cy="templates"]').first().click();
    cy.takeScreenshot("admin/notification_templates");

    cy.get("#admin_network").first().click();
    cy.takeScreenshot("admin/https");

    cy.get('[data-cy="tor"]').first().click();
    cy.takeScreenshot("admin/tor");

    cy.get('[data-cy="access_control"]').first().click();
    cy.takeScreenshot("admin/access_control");

    cy.get('[data-cy="url_redirects"]').first().click();
    cy.takeScreenshot("admin/url_redirects");

    cy.get("#admin_audit_log").first().click();
    cy.takeScreenshot("admin/audit_log");

    cy.get('[data-cy="users"]').click();
    cy.takeScreenshot("admin/audit_log_users");

    cy.get('[data-cy="reports"]').first().click();
    cy.takeScreenshot("admin/audit_log_reports");

    cy.get('[data-cy="scheduled_jobs"]').first().click();
    cy.takeScreenshot("admin/audit_log_scheduled_jobs");

    cy.logout();
  });
});

describe("Acquire screenshots necessary for user documentation - Analyst Section", () => {
  it("should capture screenshots of the analyst section", function () {
    cy.login_analyst();
    cy.takeScreenshot("analyst/home");
    cy.get("#analyst_statistics").first().click();
    cy.takeScreenshot("analyst/statistics");
    cy.logout();
  });
});

describe("Acquire screenshots necessary for user documentation - Custodian Section", () => {
  it("should capture screenshots of the custodian section", function () {
    cy.login_custodian();
    cy.takeScreenshot("custodian/home");
    cy.get("#custodian_requests").first().click();
    cy.takeScreenshot("custodian/requests");
    cy.logout();
  });
});

describe("Acquire screenshots necessary for user documentation - Recipient Section", () => {
  it("should capture screenshots of the recipient section", function () {
    cy.login_receiver();
    cy.takeScreenshot("recipient/home");
    cy.get("#recipient_settings").click();
    cy.takeScreenshot("recipient/settings");
    cy.visit("/#/recipient/reports");
    cy.get("#tip-0").first().click();
    cy.get('[id="tip-action-mask"]').should('be.visible').click();
    cy.get("#edit-question").should('be.visible').first().click();
    cy.takeScreenshot("recipient/masking-popup", ".modal");
    cy.get("#close-redact-modal").should('be.visible').first().click();
    cy.logout();
  });
});
