describe("IDP/Keycloak admin configuration workflow", () => {
  const issuerUrl = "http://127.0.0.1:9090/realms/globaleaks";
  const keycloakOrigin = "http://127.0.0.1:9090";

  function authenticateWithKeycloak() {
    cy.origin(
      keycloakOrigin,
      {
        args: {
          username: "admin",
          password: Cypress.env("keycloak_user_password")
        }
      },
      ({username, password}) => {
        cy.location("pathname").should("include", "/protocol/openid-connect/auth");
        cy.get("input#username").type(username);
        cy.get("input#password").type(password);
        cy.get('input[type="submit"],button[type="submit"]').click();
      }
    );
  }

  it("keeps login, logout, and signup IDP redirects on the intended route", () => {
    cy.login_admin();

    cy.visit("/#/admin/sites");
    cy.get('[data-cy="options"]').should("be.visible").click();
    cy.get('input[name="enable_signup"]').then(input => {
      if (!input.is(":checked")) {
        cy.wrap(input).click();
        cy.get("#save").click();
      }
    });

    cy.visit("/#/admin/settings");
    cy.get('[data-cy="authentication"]').click().should("be.visible");
    cy.get('select[name="auth_type"]').select("idp");
    cy.get('#idp-issuer').clear().type(issuerUrl);
    cy.get("#save").should("not.be.disabled").click();
    cy.logout();

    authenticateWithKeycloak();
    cy.get("#default-login-password").type(Cypress.env("user_password"));
    cy.get("#login-button").first().click();
    cy.get("#LogoutLink").should("be.visible");

    cy.logout();
    cy.visit("/#/signup");
    cy.contains("button", "Authenticate with IDP").should("be.visible").click();
    authenticateWithKeycloak();
    cy.location("hash").should("include", "/signup");
    cy.get('input[name="subdomain"]').should("be.visible");

    cy.visit("/#/login");
    cy.get("#default-login-password").type(Cypress.env("user_password"));
    cy.get("#login-button").first().click();

    cy.get("#LogoutLink").should("be.visible");
    cy.visit("/#/admin/settings");
    cy.get('[data-cy="authentication"]').click().should("be.visible");
    cy.get('select[name="auth_type"]').select("globaleaks");
    cy.get("#save").should("not.be.disabled").click();

    cy.visit("/#/admin/sites");
    cy.get('[data-cy="options"]').should("be.visible").click();
    cy.get('input[name="enable_signup"]').then(input => {
      if (input.is(":checked")) {
        cy.wrap(input).click();
        cy.get("#save").click();
      }
    });

    cy.logout();

    cy.login_admin();
    cy.visit("/#/admin/settings");
    cy.get('[data-cy="authentication"]').click().should("be.visible");
    cy.get('select[name="auth_type"]').should("have.value", "globaleaks");
    cy.get('#idp-issuer').should('not.exist');
    cy.logout();
  });
});
