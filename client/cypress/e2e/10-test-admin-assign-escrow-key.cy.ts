describe("key escrow assignment and revocation", () => {
  it("should assign escrow key to Admin 2", () => {
    cy.login_admin();

    // The administrators authorized to change user passwords are named among
    // the advanced settings of the site, and no longer on the account itself
    cy.visit("/#/admin/settings");
    cy.get('[data-cy="advanced"]').click().should("be.visible").click();

    cy.get('input[name="node.dataModel.escrow"]').check();

    cy.get(".selection-editor-add").click();
    cy.get("ng-select").last().click();
    cy.get("div.ng-option").contains("Admin2").click();

    cy.get("[name='secret']").type(Cypress.env("user_password"));
    cy.get("#confirm").click();

    // Confirming reloads the configuration and the page returns to its first
    // tab: the authorization is read back where it is set
    cy.get('[data-cy="advanced"]').click().should("be.visible").click();
    cy.get("ul.selection-list li").should("contain", "Admin2");

    cy.logout();
  });
});
