describe("key escrow assignment", () => {
  // The authorization to change the passwords of the users is granted from the list of the users
  it("should authorize Admin2 to change user passwords", () => {
    cy.login_admin();
    cy.visit("/#/admin/settings");
    cy.get("form[name='contentForm']").should("be.visible");
    cy.openTab("advanced");

    cy.get(".selection-editor-add").first().click();
    cy.get("ng-select").last().click();
    cy.get("div.ng-option").contains("Admin2").click();

    // the operation is confirmed with the password of the administrator
    cy.get("[name='secret']").should("be.visible").clear().type(Cypress.env("user_password"));
    cy.get("#confirm").click();

    // the confirmed operation reloads the component and the navigation returns
    // to its first tab: the advanced one is reopened to read the outcome
    cy.waitForPageIdle();
    cy.openTab("advanced");
    cy.get("ul.selection-list li").should("contain", "Admin2");

    cy.logout();
  });
});
