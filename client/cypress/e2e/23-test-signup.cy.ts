import {t} from "../support/i18n";
describe("Admin Enable Signup", function() {
  it("should enable signup", function() {
    cy.login_admin();

    cy.visit("/#/admin/sites");
    cy.openTab("options");
    cy.get('input[name="rootdomain"]').clear().type("domain.tld");
    // the state may already be enabled from an earlier spec: set, not toggled
    cy.get('input[name="enable_signup"]').then(($i) => { if (!$i.is(":checked")) cy.wrap($i).click(); });

    // enabling the signup redraws the section and returns to the first tab: reopen the options
    cy.waitForPageIdle();
    cy.openTab("options");
    // the toggle binds its name through NgModel: reached by its label
    cy.contains(".form-group", t("Enable terms of service")).first()
      .find('input[type="checkbox"]').first()
      .then(($i) => { if (!$i.is(":checked")) cy.wrap($i).click(); });
    cy.get("#signup-tos1-title").clear().type("Terms and Conditions");
    cy.get("#signup-tos1-checkbox-label").clear().type("I've ready and I accept the [Terms and Conditions](https://globaleaks.org)");
    cy.takeScreenshot("admin/signup_configuration");
    cy.get("#save").click();

    cy.logout();
  });
});

// The accreditation page becomes reachable by electing it as the home
describe("Admin elect the signup as the home of the platform", function() {
  // The election of the signup as the home of the platform, and its customized texts
  it("should elect the signup as the home of the platform", function() {
    cy.login_admin();

    cy.visit("/#/admin/settings");
    cy.openTab("advanced");
    cy.get("#homepage-input").should("be.visible").select("/signup");
    cy.takeScreenshot("admin/advanced_settings_homepage_detail", '.form-group:has(#homepage-input)');
    cy.get("#save").click();

    cy.visit("/#/admin/settings");
    cy.openTab("advanced");
    cy.get("#homepage-input").should("have.value", "/signup");

    cy.logout();
  });
});

describe("User Perform Signup", function() {
  it("should perform signup", function() {
    cy.visit("/#/");

    // The home guard reads the public configuration before it is resolved: on a cold visit either
    // page may appear
    cy.get("#SignupForm, #WhistleblowingButton", { timeout: 20000 }).should("be.visible");
    cy.get("body").then(($body) => {
      if (!$body.find("#SignupForm").length) {
        cy.visit("/#/signup");
      }
    });
    cy.get("#SignupForm").should("be.visible");

    cy.takeScreenshot("admin/signup_form");

    cy.takeScreenshot("forward/homepage");
    cy.takeScreenshot("forward/homepage_texts_detail", "#HeaderBox");
    cy.takeScreenshot("forward/signup_form", "#SignupForm");

    cy.get('input[name="subdomain"]').type("test");
    cy.get('input[name="organization_name"]').type("Test Organization");
    cy.get('input[name="name"]').type("Name");
    cy.get('input[name="surname"]').type("Surname");
    cy.get('input[name="mail_address"]').type("test@example.net");
    cy.get('input[name="email"]').type("test@example.net");

    // the address is entered twice; the row holding both is the ancestor, not every row
    cy.takeScreenshot("forward/signup_email_detail", '.row:has(> .form-group > #signup-email)');

    cy.get(".ButtonNext").click();

    cy.contains(".title", "Terms and Conditions").should("be.visible");
    cy.get(".title").should("be.visible");
    cy.takeScreenshot("forward/signup_activation");
  });
});

describe("Admin Disable Signup", function() {
  it("should disable signup", function() {
    cy.visit("/#/login");
    cy.login_admin();

    // the option is offered only while the signup is enabled: restore the default first
    cy.visit("/#/admin/settings");
    cy.openTab("advanced");
    cy.get("#homepage-input").should("be.visible").select("/");
    // saving navigates the platform to itself: wait for it before leaving
    cy.get("#save").click();
    cy.get('[data-cy="advanced"]', {timeout: 20000}).should("not.have.class", "active");

    cy.visit("/#/admin/sites");
    cy.openTab("options");
    cy.get('input[name="enable_signup"]').click();
    // disabling removes the registrations tab and returns to the first tab: reopen the options
    cy.waitForPageIdle();
    cy.openTab("options");
    cy.get("#save").click();

    cy.logout();
    cy.waitForUrl("/#/login")
    cy.visit("/#/");

  });
});
