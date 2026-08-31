// The delegation of the authentication is a configuration of the whole
// platform: while it is on, every account authenticates through the provider
// and no local login is left to take it off again. This spec therefore runs
// last, and puts back through the session it holds what it changes.
describe("IDP/Keycloak admin configuration workflow", () => {
  const issuerUrl = "http://127.0.0.1:9090/realms/globaleaks";
  const clientId = "globaleaks";

  // The session held before the configuration is written is what puts the
  // platform back, whatever the outcome of the test.
  const restore_configuration = () => {
    cy.get("@adminSession").then((session) => {
      const headers = {"x-session": String(session)};

      cy.request({method: "GET", url: "/api/admin/node", headers}).then(({body}) => {
        cy.request({
          method: "PUT",
          url: "/api/admin/node",
          headers,
          body: {...body, idp: false, idp_issuer: "", idp_client_id: "", idp_provisioning: false}
        });
      });
    });
  };

  after(() => {
    restore_configuration();
  });

  // TC.4: the external organizations authenticate through the homepage of the
  // forwarding function with the credentials held by their identity provider.
  // What is exercised here is the configuration of that provider: the identity
  // spent on the accreditation page is the one of the profile assigned to the
  // registrations, and reaching it end to end asks of the test environment a
  // realm whose accounts are the accounts of the platform (see Q-12).
  it("configures the identity provider the authentication is delegated to", () => {
    cy.intercept("POST", "/api/auth/authentication").as("adminLogin");
    cy.login_admin();
    cy.wait("@adminLogin").its("response.body.id").as("adminSession");

    cy.visit("/#/admin/settings");
    cy.openTab("authentication");

    // the provider is described while the delegation is off: the configuration
    // is locked as soon as it is on, and enabling it is a separate act
    cy.get("#idp-issuer").clear().type(issuerUrl);
    cy.get("#idp-client-id").clear().type(clientId);
    cy.get("#save").click();
    cy.waitForPageIdle();

    cy.takeScreenshot("admin/authentication_settings");
    cy.takeScreenshot("admin/authentication_settings_detail", "#Content");

    // what has been written is what the platform holds
    cy.visit("/#/admin/settings");
    cy.openTab("authentication");
    cy.get("#idp-issuer").should("have.value", issuerUrl);
    cy.get("#idp-client-id").should("have.value", clientId);

    // the delegation is offered, and refused while the description is missing
    cy.get("#idp-enable").should("not.be.disabled");

    restore_configuration();

    cy.logout();
  });
});
