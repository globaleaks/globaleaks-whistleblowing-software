// Every field of the tab, the value the test gives it and where the site shows it
const TEXTS = {
  "#project-name-input": "Example Organization",
  "#node-description": "The reporting site of the example organization",
  "#node-header-title": "Report a wrongdoing",
  "#node-presentation": "Welcome to the reporting site",
  "#node-whistleblowing-question": "Have you witnessed a wrongdoing?",
  "#whistleblowing-button-input": "File a report",
  "#node-disclaimer-text": "Read this before you report",
  "#footer-whistleblowing-policy": "/whistleblowing-policy",
  "#footer-privacy-policy": "https://www.globaleaks.org/privacy",
  "#node-footer": "Example Organization, Example Street 1"
};

describe("admin configure settings", () => {
  it("should configure the texts of the site", () => {
    const original: Record<string, string> = {};

    cy.login_admin();
    cy.visit("#/admin/settings");
    cy.intercept("PUT", "**/api/admin/node").as("saveNode");

    for (const [selector, value] of Object.entries(TEXTS)) {
      cy.get(selector).invoke("val").then(text => {
        original[selector] = text as string;
      });
      cy.get(selector).clear().type(value);
    }

    // An address that is neither local nor on https is refused
    cy.get("#footer-privacy-policy").clear().type("http://www.globaleaks.org/privacy").should("have.class", "is-invalid");
    cy.get("#footer-privacy-policy").clear().type(TEXTS["#footer-privacy-policy"]).should("not.have.class", "is-invalid");

    cy.get("#save_settings").click();
    cy.wait("@saveNode");
    cy.logout();

    cy.visit("/#/");
    cy.title().should("eq", `${TEXTS["#project-name-input"]} - ${TEXTS["#node-header-title"]}`);
    cy.get('meta[name="description"]').should("have.attr", "content", TEXTS["#node-description"]);
    cy.get("#ProjectTitle").should("contain", TEXTS["#project-name-input"]);
    cy.get("#Presentation").should("contain", TEXTS["#node-presentation"]);
    cy.get("#WhistleblowingQuestion").should("contain", TEXTS["#node-whistleblowing-question"]);
    cy.get("#Policies a").first().should("have.attr", "href", TEXTS["#footer-whistleblowing-policy"]);
    cy.get("#Policies a").last().should("have.attr", "href", TEXTS["#footer-privacy-policy"]);
    cy.get("#CustomFooter").should("contain", TEXTS["#node-footer"]);

    // The disclaimer stands between the button and the questionnaire
    cy.get("#WhistleblowingButton").should("contain", TEXTS["#whistleblowing-button-input"]).click();
    cy.get(".modal").should("contain", TEXTS["#node-disclaimer-text"]);
    cy.get("#modal-action-ok").click();
    cy.get(".modal").should("not.exist");

    // The texts go back to those of the wizard, which the next specs expect
    cy.login_admin();
    cy.visit("#/admin/settings");
    cy.then(() => {
      for (const [selector, value] of Object.entries(original)) {
        cy.get(selector).invoke("val", value).trigger("input");
      }
    });
    cy.get("#save_settings").click();
    cy.wait("@saveNode");
    cy.logout();
  });
});
