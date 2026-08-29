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

  beforeEach(() => {
    cy.login_analyst();
    cy.visit("/#/analyst/statistics");
    cy.waitForPageIdle();
  });

  afterEach(() => {
    cy.logout();
  });

  it("creates, searches, edits and deletes a statistical template", () => {

    createTemplate("Template");

    cy.get("input[placeholder*='Search']").type("Template");
    cy.contains(".templateList .config-item", "Template").should("be.visible");
    cy.get("input[placeholder*='Search']").clear();

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

    cy.contains(".reportList .config-item", "Report")
      .within(() => {
        cy.get("#edit_report").click();
      });

    cy.get("input[name='label']").first().clear().type("Updated Report");
    cy.get("#save_report").first().click();
    cy.waitForPageIdle();

    cy.contains(".reportList .config-item", "Updated Report").should("be.visible");

    cy.contains(".reportList .config-item", "Updated Report")
      .within(() => {
        cy.get("#delete_report").click();
      });
    cy.waitForPageIdle();

    cy.contains(".reportList .config-item", "Updated Report").should("not.exist");
  });

});
