// The delegation of the authentication is a configuration of the whole
// platform: while it is on, every account authenticates through the provider.
// This spec therefore runs last, and puts the platform back as it found it
// whatever its own outcome, so that a failure here cannot be mistaken for a
// failure of what would have followed.
describe("IDP/Keycloak admin configuration workflow", () => {
  const issuerUrl = "http://127.0.0.1:9090/realms/globaleaks";
  const keycloakOrigin = "http://127.0.0.1:9090";

  const restore_local_authentication = () => {
    cy.visit("/#/login");
    cy.get("#default-login-password", {timeout: 20000}).should("be.visible").type(Cypress.env("user_password"));
    cy.get("#login-button").first().click();
    cy.get("#LogoutLink").should("be.visible");

    cy.visit("/#/admin/settings");
    cy.openTab("authentication");
    cy.get("body").then(($body) => {
      if ($body.find("#idp-disable").length) {
        cy.get("#idp-disable").click();
        cy.waitForPageIdle();
        cy.openTab("authentication");
      }
    });
    cy.get("#idp-reset").click();
    cy.waitForPageIdle();
    cy.get("#idp-enable").should("exist");
  };

  after(() => {
    restore_local_authentication();
  });

  function authenticateWithKeycloak() {
    cy.origin(
      keycloakOrigin,
      {
        args: {
          username: "globaleaks",
          password: "globaleaks"
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

  // TC.4: the external organizations authenticate through the homepage of the
  // forwarding function with the credentials held by their identity provider.
  // The platform delegates the authentication to the provider configured here,
  // which in the deployment of the Authority is the national digital identity
  // system; the test exercises the same delegation against a local provider.
  it("delegates to the identity provider the authentication of an accreditation", () => {
    cy.login_admin();

    // the accreditation page has to be offered, for an identity to be spent on it
    cy.visit("/#/admin/sites");
    cy.openTab("options");
    cy.get('input[name="enable_signup"]').then(input => {
      if (!input.is(":checked")) {
        cy.wrap(input).click();
        // enabling the signup redraws the section and takes the navigation
        // back to its first tab: the options are reopened before saving
        cy.waitForPageIdle();
        cy.openTab("options");
        cy.get("#save").click();
      }
    });

    // the provider is described while the delegation is off, and the delegation
    // is a separate act: the configuration is locked once it is on
    cy.visit("/#/admin/settings");
    cy.openTab("authentication");
    cy.get("#idp-issuer").clear().type(issuerUrl);
    cy.get("#idp-client-id").clear().type("globaleaks");
    cy.get("#save").click();
    cy.waitForPageIdle();

    cy.openTab("authentication");
    cy.get("#idp-enable").click();
    cy.waitForPageIdle();

    // the session is dropped without passing through the logout: with the
    // delegation on, the logout is the provider's and does not come back to
    // the login of the platform
    cy.clearCookies();
    cy.window().then((win) => win.localStorage.clear());

    // the accreditation page offers the identity instead of a set of fields
    cy.visit("/#/signup");
    cy.contains("button", "Authenticate with IDP").should("be.visible");
    cy.takeScreenshot("forward/idp_authentication");
    cy.contains("button", "Authenticate with IDP").click();

    authenticateWithKeycloak();

    cy.location("hash").should("include", "/signup");
    cy.get("#signup-name").should("be.visible");

    // the fields valued by the claims of the identity are read only
    cy.takeScreenshot("forward/idp_claims_detail", '.row:has(#signup-name)');

    // the delegation is taken off here as well as in the hook that closes the
    // spec: what the test asserts is that it can be taken off
    restore_local_authentication();
  });
});
