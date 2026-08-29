describe("recipient admin tip actions", () => {

  it("should disable antivirus", function () {
    cy.login_admin();
    cy.visit("/#/admin/settings")
    cy.get('[data-cy="antivirus"]').click().should("be.visible").click();

    cy.get('body').then($body => {
      if ($body.find('#antivirus-disable').length) {
        cy.get('#antivirus-disable').click();
      }
    });
    cy.logout();
    cy.waitForUrl("/#/login")
  });

  it("should apply grant and revoke access to selected reports for a specific recipient", function () {
    cy.login_receiver();

    cy.visit("/#/recipient/reports");

    // Filter reports
    cy.get('#search-filter-input').type("your search term");
    cy.get('#search-filter-input').clear();
    cy.get('th.TipInfoID').click();
    cy.get('#filter-context_name').click();
    cy.get('.multiselect-item-checkbox').eq(1).click();
    cy.get('.multiselect-item-checkbox').eq(0).click();
    cy.get('#filter-creation_date').click();
    cy.get('.custom-date-selector').first().click();
    cy.get('.custom-date-selector').eq(4).click({ shiftKey: true });
    cy.contains('button.btn.btn-danger', 'Reset').click();

    // Select all the reports
    cy.get('#tip-action-select-all').click();

    // Export selected reports
    cy.visit("/#/recipient/reports");
    cy.get('#tip-action-export').click();

    // Enter a report on the site
    cy.get("#tip-action-enter-report").click();
    cy.get("#InsertionForm").should("be.visible");
    cy.get(".modal-header .btn-close").click();

    cy.logout();
  });
});
