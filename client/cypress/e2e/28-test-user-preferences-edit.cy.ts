// The personal data an account carries are edited from the preferences, one at a time
describe("preferences of the account", () => {
  let originalName = "";

  it("should edit the name, the public name and the notification setting", () => {
    cy.login_admin();
    cy.visit("/#/admin/preferences");
    cy.get("#PreferencesForm").should("be.visible");

    cy.get("#Name > span > span").first().invoke("text").then(text => {
      originalName = text.trim();
    });

    // each datum is shown as text and opens to an input on request
    cy.get("#pref-name-input").should("not.exist");
    cy.get("#Name button").click();
    cy.get("#pref-name-input").clear().type("Renamed administrator");

    cy.get("#PublicName button").click();
    cy.get("#pref-public-name-input").clear().type("The administrator");

    cy.get("#pref-notification-checkbox").then($box => {
      cy.wrap($box).click();
    });

    cy.takeScreenshot("user/preferences_editing");
    cy.takeScreenshot("user/preferences_editing_detail", "#PreferencesForm");

    cy.intercept("PUT", "**/api/user/preferences").as("savePreferences");
    cy.get("#PreferencesForm button[type='submit']").click();
    cy.wait("@savePreferences").its("response.statusCode").should("be.within", 200, 299);

    // what was saved is what a fresh read returns
    cy.intercept("GET", "**/api/user/preferences").as("readPreferences");
    cy.visit("/#/admin/home");
    cy.visit("/#/admin/preferences");
    cy.wait("@readPreferences").its("response.body").then((body: any) => {
      expect(body.name).to.eq("Renamed administrator");
      expect(body.public_name).to.eq("The administrator");
    });
    cy.logout();
  });

  it("should ask the validation of a new email address", () => {
    cy.login_admin();
    cy.visit("/#/admin/preferences");

    cy.get("#EmailAddress button").click();
    cy.get("#pref-email-input").clear().type("renamed@example.org");

    cy.intercept("PUT", "**/api/user/preferences").as("savePreferences");
    cy.get("#PreferencesForm button[type='submit']").click();
    cy.wait("@savePreferences").its("response.statusCode").should("be.within", 200, 299);

    // the address changes once the message sent to it is followed: until then it is pending
    cy.intercept("GET", "**/api/user/preferences").as("readPreferences");
    cy.visit("/#/admin/home");
    cy.visit("/#/admin/preferences");
    cy.wait("@readPreferences").its("response.body.change_email_address").should("eq", "renamed@example.org");
    cy.takeScreenshot("user/preferences_email_validation_detail", "#EmailAddress");
    cy.logout();
  });

  it("should give the account its name back", () => {
    cy.login_admin();
    cy.visit("/#/admin/preferences");

    cy.get("#Name button").click();
    cy.get("#pref-name-input").clear().type(originalName);
    cy.get("#PublicName button").click();
    cy.get("#pref-public-name-input").clear().type(originalName);
    cy.get("#pref-notification-checkbox").click();

    cy.intercept("PUT", "**/api/user/preferences").as("savePreferences");
    cy.get("#PreferencesForm button[type='submit']").click();
    cy.wait("@savePreferences").its("response.statusCode").should("be.within", 200, 299);
    cy.logout();
  });
});
