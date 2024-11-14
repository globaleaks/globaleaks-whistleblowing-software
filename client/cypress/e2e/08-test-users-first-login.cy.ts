describe("Recipient first login", () => {
  it("should require password change upon successful authentication", () => {
    cy.wait(2000)
    cy.login_receiver("Recipient", Cypress.env("init_password"), "#/login", true);
    cy.takeScreenshot("user/password");
    cy.get('input[name="changePasswordArgs.password"]').should('be.visible', { timeout: 10000 }).clear().type(Cypress.env("user_password"));
    cy.get('input[name="changePasswordArgs.confirm"]').type(Cypress.env("user_password"));
    cy.get('button[name="submit"]').click();
    cy.waitForUrl("/recipient/home");
    cy.logout();
  });

  it("should be able to login with the new password", () => {
    cy.login_receiver();
  });

  it("should be able to retrieve the account recovery key", () => {
    cy.login_receiver("Recipient", Cypress.env("user_password"), "#/login", true);
    cy.waitForUrl("/recipient");
    cy.visit("/#/recipient/preferences");
    cy.takeScreenshot("user/preferences");
    cy.get( "#account_recovery_key").click();
    cy.get("[name='secret']").type(Cypress.env("user_password"));
    cy.get("#confirm").click();
    cy.takeScreenshot("user/recoverykey", ".modal");
    cy.get("#close").click();
    cy.get("[name='two_factor']").click();
    cy.takeScreenshot("user/2fa", ".modal");
    cy.get("#close").click();
  });
});

describe("Recipient2 first login", () => {
  it("should require password change upon successful authentication", () => {
    cy.login_receiver("Recipient2", Cypress.env("init_password"), "#/login", true);
    cy.get('[name="changePasswordArgs.password"]').type(Cypress.env("user_password"));
    cy.get('[name="changePasswordArgs.confirm"]').type(Cypress.env("user_password"));
    cy.get('button[name="submit"]').click();

    cy.url().should("include", "/recipient/home");
    cy.get("#PreferencesLink").click();
    cy.get(".password").click();
    cy.get('[name="changePasswordArgs.current"]').type(Cypress.env("user_password"));
    cy.get('[name="changePasswordArgs.password"]').type(Cypress.env("init_password"));
    cy.get('[name="changePasswordArgs.confirm"]').type(Cypress.env("init_password"));
    cy.get('button[name="submit"]').click();
    cy.logout();
  });
});

describe("Custodian first login", () => {
  it("should require password change upon successful authentication", () => {
    cy.login_custodian("Custodian", Cypress.env("init_password"), "#/login", true);
    cy.get('[name="changePasswordArgs.password"]').should('be.visible', { timeout: 10000 }).type(Cypress.env("user_password"));
    cy.get('[name="changePasswordArgs.confirm"]').type(Cypress.env("user_password"));
    cy.get('button[name="submit"]').click();
    cy.url().should("include", "/custodian/home");
    cy.logout();
  });
});

describe("Admin2 first login", () => {
  it("should require password change upon successful authentication", () => {
    cy.login_custodian("Admin2", Cypress.env("init_password"), "#/login", true);
    cy.get('[name="changePasswordArgs.password"]').type(Cypress.env("user_password"));
    cy.get('[name="changePasswordArgs.confirm"]').type(Cypress.env("user_password"));
    cy.get('button[name="submit"]').click();
    cy.url().should("include", "/admin/home");
    cy.logout();
  });
});

describe("Analyst first login", () => {
  it("should require password change upon successful authentication", () => {
    cy.login_analyst("Analyst", Cypress.env("init_password"), "#/login", true);
    cy.get('[name="changePasswordArgs.password"]').should('be.visible', { timeout: 10000 }).type(Cypress.env("user_password"));
    cy.get('[name="changePasswordArgs.confirm"]').type(Cypress.env("user_password"));
    cy.get('button[name="submit"]').click();
    cy.url().should("include", "/analyst/home");
    cy.logout();
  });
});

describe("Resp_Accreditation first login", () => {
  it("should require password change upon successful authentication", () => {
    cy.login_accreditor("Resp_Accreditation", Cypress.env("init_password"), "#/login", true);
    cy.get('[name="changePasswordArgs.password"]').should('be.visible', { timeout: 10000 }).type(Cypress.env("user_password"));
    cy.get('[name="changePasswordArgs.confirm"]').type(Cypress.env("user_password"));
    cy.get('button[name="submit"]').click();
    cy.url().should("include", "/accreditor/home");
    cy.logout();
  });
});