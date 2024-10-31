describe("globaLeaks setup wizard", () => {
  it("should allow the user to setup the wizard", () => {
    cy.visit("/#/");

    cy.get("#PageTitle").should("be.visible");

    if (Cypress.env('language')!="en") {
      cy.get('#language-picker-select').click();
      cy.get(`[data-cy="${Cypress.env('language')}"]`).trigger('click');
    }

    cy.takeScreenshot("wizard/1");

    cy.get(".ButtonNext").click();

    cy.takeScreenshot("wizard/2");

    cy.get('[name="node_name"]').type("GLOBALEAKS");

    cy.get(".ButtonNext").click();

    cy.takeScreenshot("wizard/3");

    cy.get('[name="admin_username"]').type("admin");
    cy.get('[name="admin_name"]').type("Admin");
    cy.get('[name="admin_mail_address"]').type("globaleaks-admin@mailinator.com");
    cy.get('[name="admin_password"]').type(Cypress.env('user_password'));
    cy.get('[name="admin_password_check"]').type(Cypress.env('user_password'));

    cy.get(".ButtonNext").click();

    cy.takeScreenshot("wizard/4");

    cy.get('[name="skip_recipient_account_creation_checkbox"]').click();

    cy.get(".ButtonNext").click();

    cy.takeScreenshot("wizard/5");

    cy.get('.tos-agreement-input').click();

    cy.get(".ButtonNext").click();

    cy.takeScreenshot("wizard/6");
    cy.get('button[name="proceed"]').should('be.visible').click();

    cy.waitForUrl("admin/home")
    cy.logout();
  });
});
