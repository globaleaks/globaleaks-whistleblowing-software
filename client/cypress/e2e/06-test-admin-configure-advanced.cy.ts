describe("admin configure advanced settings", () => {
  it("should perform main configuration", () => {
    cy.login_admin();
    cy.visit("/#/admin/settings");
    cy.get('[data-cy="advanced"]').click().should("be.visible", { timeout: 10000 }).click();
    cy.get('input[name="node.dataModel.allow_indexing"]').click();
    cy.get("#save").click();
  });
});

describe("admin disable submissions", () => {
  it("should disable submission", () => {
    cy.login_admin();
    cy.visit("/#/admin/settings");
    cy.get('[data-cy="advanced"]').click().should("be.visible", { timeout: 10000 }).click();

    cy.get('input[name="disable_submissions"]').click();
    cy.get("#save").click();

    cy.get('[data-cy="advanced"]').click().should('be.visible', { timeout: 10000 }).click();

    cy.get('input[name="disable_submissions"]').should("be.visible").should("be.checked");
    cy.logout();
    cy.waitForUrl("/#/login")
    cy.visit("/#/");
    cy.get("#submissions_disabled").should("be.visible");

  });
});

describe("admin enable submissions", () => {
  it("should enable submission", () => {
    cy.login_admin();
    cy.waitForUrl("/#/admin/home")
    cy.visit("/#/admin/settings")
    cy.get('[data-cy="advanced"]').click().should("be.visible", { timeout: 10000 }).click();

    cy.get('input[name="disable_submissions"]').click();
    cy.get("#save").click();
    cy.waitForLoader()
    cy.get('[data-cy="advanced"]').click().should('be.visible', { timeout: 10000 }).click();

    cy.get('input[name="disable_submissions"]').should("be.visible").should("not.be.checked");
    cy.logout();
    cy.waitForUrl("/#/login")

    cy.visit("/#/");
    cy.get("#WhistleblowingButton").should("be.visible");
  });
});

describe("Should browser opens a pop while clicking the support icon", () => {
  it("should open a pop-up modal", () => {
    cy.login_admin();
    cy.waitForUrl("/#/admin/home");
    cy.visit("/#/admin/settings");
    cy.get('[data-cy="advanced"]').click().should("be.visible", { timeout: 10000 }).click();

    cy.get('input[name="customSupportURL"]').clear();

    cy.get("#save").click();
    cy.get('[data-cy="advanced"]').click().should("be.visible", { timeout: 10000 }).click();

    cy.get('input[name="customSupportURL"]')
      .invoke("val")
      .should("equal", "");

    cy.get("#SupportLink").click();
    cy.get(".modal").should("be.visible");

    cy.get('textarea[name="message"]').type("test message");
    cy.get(".modal #modal-action-ok").click();

    cy.get("#sent").should("be.visible");

    cy.get('#modal-action-cancel').should('be.visible').click();
    cy.logout();
    cy.waitForUrl('/login');
  });
});

describe("Validating custom support url", () => {
  it("Enter custom support url and browser", () => {
    cy.login_admin();
    cy.visit("/#/admin/settings");
    cy.get('[data-cy="advanced"]').click().should("be.visible", { timeout: 10000 }).click();

    cy.get('input[name="customSupportURL"]').clear();
    cy.get('input[name="customSupportURL"]').type(
      "https://www.globaleaks.org/"
    );

    cy.get("#save").click();
    cy.waitForLoader();
    cy.get('[data-cy="advanced"]').click().should('be.visible', { timeout: 10000 }).click();

    cy.get('input[name="customSupportURL"]')
      .invoke("val")
      .should("equal", "https://www.globaleaks.org/");
    cy.logout();

  });
});
describe("admin enable scoring system", () => {
  it("should enable scoring system", () => {
    cy.login_admin();
    cy.visit("/#/admin/settings");
    cy.get('[data-cy="advanced"]').click().should("be.visible", { timeout: 10000 }).click();
    cy.get('#scoring_system').click();
    cy.get("#save").click();
    cy.logout();
  });
});

describe("admin add and remove disclaimer", function () {
  it("should add disclaimer", function () {
    cy.login_admin();
    cy.visit("/#/admin/settings");
    cy.get('textarea[name="nodeResolver.dataModel.disclaimer_text"]').type("disclaimer_text");
    cy.get("#save_settings").click();
    cy.visit("#/");
    cy.get("#WhistleblowingButton").click();
    cy.get('#modal-action-ok').click();
    cy.login_admin();
    cy.visit("/#/admin/settings");
    cy.get('textarea[name="nodeResolver.dataModel.disclaimer_text"]').clear();
    cy.get("#save_settings").click();
    cy.logout();
  });
});

describe("admin add and remove user privacy policy", function () {
  it("should add and remove user privacy policy", function () {
    cy.login_admin();
    cy.visit("/#/admin/users");
    cy.get('[data-cy="options"]').click();
    cy.get('textarea[name="nodeData.user_privacy_policy_text"]').type("user_privacy_policy_text");
    cy.get('input[name="nodeData.user_privacy_policy_url"]').type("user_privacy_policy_url");
    cy.get("#save_user_policy").click();
    cy.visit("/#/admin/home");
    cy.get('input[name="tos2"]').check();
    cy.get('#modal-action-ok').click();
    cy.get("#admin_users").click();
    cy.get('[data-cy="options"]').click();
    cy.get('textarea[name="nodeData.user_privacy_policy_text"]').clear();
    cy.get('input[name="nodeData.user_privacy_policy_url"]').clear();
    cy.get("#save_user_policy").click();
    cy.logout();
  });
});
