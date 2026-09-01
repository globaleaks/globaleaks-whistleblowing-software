describe("admin configure languages", () => {
  it("should configure languages", () => {
    cy.login_admin();
    cy.visit("/#/admin/settings");
    cy.get('[data-cy="languages"]').click();

    // The selector closes on every choice: it is opened again for each of the
    // languages the site is given
    const enable = (language: string) => {
      cy.get(".add-language-btn").click();
      cy.get("#LanguageAdder ng-select").click();
      cy.get('div.ng-option').contains(language).click();
      cy.get('ul.selection-list li').should('contain', language);
    };

    if (Cypress.env('language')!=="en") {
      enable('English [en]');
    }

    if (Cypress.env('language')!=="it") {
      enable('Italian [it]');
    }

    if (Cypress.env('language')!=="de") {
      enable('German [de]');
    }

    cy.get("#save_language").click();

    cy.waitForUrl("/#/admin/settings");
    cy.get('#LanguagePickerBox').should('be.visible').find('ng-select').last().click().get('ng-dropdown-panel').contains('Italiano').click();
    cy.waitForUrl("/#/admin/settings");
    cy.get('[name="node.dataModel.header_title_homepage"]').should('be.visible').and('have.value', '').clear().type("TEXT1_IT").should('have.value', 'TEXT1_IT');
    cy.get('[name="node.dataModel.presentation"]').should('be.visible').and('have.value', '').clear().type("TEXT2_IT").should('have.value', 'TEXT2_IT');
    cy.get('button.btn.btn-primary').eq(0).get("#save_settings").click();

    cy.logout();
  });
});

describe("Whistleblower Navigate Home Page in EN", () => {
  it("should see page properly internationalized", () => {

    cy.visit("/#/?lang=en");
    cy.get('html').should('have.attr', 'lang', 'en');
    cy.get('div').should('not.contain', 'TEXT1_IT');
    cy.get('div').should('not.contain', 'TEXT2_IT');
  });
});

describe("Whistleblower Navigate Home Page in IT", () => {
  it("should see page properly internationalized", () => {
    cy.visit("/#/?lang=it");
    cy.get('html').should('have.attr', 'lang', 'it');
    cy.contains("div", "TEXT1_IT").should("exist");
    cy.contains("div", "TEXT2_IT").should("exist");
  });
});

describe("admin configure languages", () => {
  it("should reset internationalization texts", () => {
    cy.login_admin();

    cy.waitForUrl("/#/admin/home");
    cy.visit("/#/admin/settings");
    cy.get('#ngb-nav-6').should('be.visible')
    cy.get('#LanguagePickerBox').should('be.visible').find('ng-select').last().click().get('ng-dropdown-panel').contains('Italian').click();
    cy.get('[name="node.dataModel.header_title_homepage"]').should('be.visible').and('have.value', 'TEXT1_IT').clear().should('have.value', '');
    cy.get('[name="node.dataModel.presentation"]').should('be.visible').and('have.value', 'TEXT2_IT').clear().should('have.value', '');
    cy.get('button.btn.btn-primary').eq(0).get("#save_settings").click();

    cy.logout();
  });
});
