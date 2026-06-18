describe("admin login", () => {
  it("should login as admin", () => {
    cy.login_admin();

    cy.visit("#/admin/preferences");
    cy.get("#account_recovery_key").click();
    cy.get("[name='secret']").type(Cypress.env("user_password"));
    cy.get("#confirm").click();
    cy.get('src-encryption-recovery-key').should('exist');

    // The recovery key is shown but hidden by default.
    cy.get('#AccountRecoveryKey').should('be.visible').and('have.attr', 'type', 'password');
    cy.takeScreenshot("admin/recoverykey", ".modal-dialog");

    // The show/hide toggle reveals and re-hides the recovery key.
    cy.get('#toggle-visibility').click();
    cy.get('#AccountRecoveryKey').should('have.attr', 'type', 'text');
    cy.takeScreenshot("admin/recoverykey_revealed", ".modal-dialog");
    cy.get('#toggle-visibility').click();
    cy.get('#AccountRecoveryKey').should('have.attr', 'type', 'password');

    cy.get("#close").click();

    cy.logout();
  });
});
