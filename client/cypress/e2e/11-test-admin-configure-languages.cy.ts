describe("admin configure languages", () => {
  it("should configure languages", () => {
    cy.login_admin();
    cy.visit("/#/admin/settings");
    cy.get('[data-cy="languages"]').click();
    cy.get(".add-language-btn").click();

    if (Cypress.env('language')!=="en") {
      cy.get("body").click("top");
      cy.get('ng-select').last().click();
      cy.get('div.ng-option').contains('English [en]').click();
      cy.get('ul.selection-list li').should('contain', 'English [en]');
    }

    if (Cypress.env('language')!=="it") {
      cy.get("body").click("top");
      cy.get('ng-select').last().click();
      cy.get('div.ng-option').contains('Italian [it]').click();
      cy.get('ul.selection-list li').should('contain', 'Italian [it]');
    }

    if (Cypress.env('language')!=="de") {
      cy.get("body").click("top");
      cy.get('ng-select').last().click();
      cy.get('div.ng-option').contains('German [de]').click();
      cy.get('ul.selection-list li').should('contain', 'German [de]');
    }

    cy.get("#save_language").click();

    cy.waitForUrl("/#/admin/settings");
    cy.get('#LanguagePickerBox').should('be.visible').find('ng-select').last().click().get('ng-dropdown-panel').contains('Italiano').click();
    cy.get('[name="node.dataModel.header_title_homepage"]').clear().type("TEXT1_IT");
    cy.get('[name="node.dataModel.presentation"]').clear().type("TEXT2_IT");
    cy.get('button.btn.btn-primary').eq(0).get("#save_settings").click();

    cy.logout();
  });
});

describe("Whistleblower Navigate Home Page", () => {
  it("should see page properly internationalized", () => {

    cy.visit("/#/?lang=en");
    cy.reload(true);
    cy.get('div').should('not.contain', 'TEXT1_IT');
    cy.get('div').should('not.contain', 'TEXT2_IT');

    cy.visit("/#/?lang=it");
    cy.reload(true);
    cy.contains("div", "TEXT1_IT").should("exist");
    cy.contains("div", "TEXT2_IT").should("exist");
  });
});

describe("admin configure languages", () => {
  it("should reset internationalization texts", () => {
    cy.login_admin();

    cy.visit("/#/admin/settings");
    cy.waitForUrl("/#/admin/settings");
    cy.get('#LanguagePickerBox').should('be.visible', { timeout: 10000 }).find('ng-select').last().click().get('ng-dropdown-panel').contains('Italian').click();
    cy.get('[name="node.dataModel.header_title_homepage"]').clear();
    cy.get('[name="node.dataModel.presentation"]').clear();
    cy.get('button.btn.btn-primary').eq(0).get("#save_settings").click();

    cy.logout();
  });
});
