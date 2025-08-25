describe("IDP/Keycloak admin configuration workflow", () => {
  const issuerUrl = "http://127.0.0.1:9090/realms/globaleaks";
  const redirectUrl = "https://127.0.0.1:8443/#/login";

  it("enables IDP, logs in/out via Keycloak, disables IDP, and verifies config reset", () => {
    cy.login_admin();
    cy.visit("/#/admin/settings");
    cy.get('[data-cy="idp"]').click().should("be.visible");
    cy.get('#idp-enable').check({ force: true });
    cy.get('#idp-issuer').clear().type(issuerUrl);
    cy.get('#idp-redirect').clear().type(redirectUrl);
    cy.get("#save").click();
    cy.logout();

    cy.visit("/#/login");
    cy.login_keycloak();
    
    cy.wait(2000);
    cy.visit("/#/admin/settings");
    cy.get('[data-cy="idp"]').click().should("be.visible");
    cy.get('#idp-enable').uncheck({ force: true });
    cy.get('#idp-issuer').clear();
    cy.get('#idp-redirect').clear();
    cy.get("#save").click();
    cy.logout();

    cy.login_admin();
    cy.visit("/#/admin/settings");
    cy.get('[data-cy="idp"]').click().should("be.visible");
    cy.get('#idp-enable').should('not.be.checked');
    cy.get('#idp-issuer').should('have.value', '');
    cy.get('#idp-redirect').should('have.value', '');
    cy.logout();
  });
});