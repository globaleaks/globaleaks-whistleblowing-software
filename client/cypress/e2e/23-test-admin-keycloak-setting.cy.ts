describe("IDP/Keycloak admin configuration workflow", () => {
  const issuerUrl = "http://127.0.0.1:9090/realms/globaleaks";

  it("enables IDP, logs in/out via Keycloak, disables IDP, and verifies config reset", () => {
    cy.login_admin();
    cy.visit("/#/admin/settings");
    cy.get('[data-cy="authentication"]').click().should("be.visible");
    cy.get('select[name="auth_type"]').select("idp");
    cy.get('#idp-issuer').clear().type(issuerUrl);
    cy.get("#save").should("not.be.disabled").click();
    cy.logout();

    cy.login_keycloak();
    cy.get("#default-login-password").type(Cypress.env("user_password"));
    cy.get("#login-button").first().click();

    cy.get("#LogoutLink").should("be.visible");
    cy.visit("/#/admin/settings");
    cy.get('[data-cy="authentication"]').click().should("be.visible");
    cy.get('select[name="auth_type"]').select("globaleaks");
    cy.get("#save").should("not.be.disabled").click();
    cy.logout();

    cy.login_admin();
    cy.visit("/#/admin/settings");
    cy.get('[data-cy="authentication"]').click().should("be.visible");
    cy.get('select[name="auth_type"]').should("have.value", "globaleaks");
    cy.get('#idp-issuer').should('not.exist');
    cy.logout();
  });
});
