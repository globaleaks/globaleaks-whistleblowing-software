describe("recipient admin tip actions", () => {
  it("should apply grant and revoke access to selected reports for a specific recipient", function () {
    cy.login_receiver();

    cy.visit("/#/recipient/reports");

    // Filter reports
    cy.get('#search-filter-input').type("your search term");
    cy.get('#search-filter-input').clear();
    cy.get('th.TipInfoID').click();
    cy.get('#tip-action-filter-channel').click();
    cy.get('.multiselect-item-checkbox').eq(1).click();
    cy.get('.multiselect-item-checkbox').eq(0).click();
    cy.get('#tip-action-filter-report-date').click();
    cy.get('.custom-date-selector').first().click();
    cy.get('.custom-date-selector').eq(4).click({ shiftKey: true });
    cy.contains('button.btn.btn-danger', 'Reset').click();

    // Select all the reports
    cy.get('#tip-action-select-all').click();

    // Export selected reports
    cy.visit("/#/recipient/reports");
    cy.get('#tip-action-export').click();

    // Act on behalf of whistleblower
    cy.get("#tip-action-act-as-whistleblower").click();

    cy.logout();
  });
});
