describe("Audit Log - View Details Modal", () => {
  it("should perform some configuration then open and display the details modal correctly", () => {
    cy.login_admin();
    cy.visit("/#/admin/settings");
    cy.get('[data-cy="advanced"]').click().should("be.visible").click();
    cy.get('input[name="node.dataModel.allow_indexing"]').click();
    cy.get("#save").click();
 
    cy.visit("/#/admin/auditlog");

    cy.get("table tbody tr").should("have.length.greaterThan", 0);

    cy.get(".fa-eye").first().click();

    cy.takeScreenshot("admin/audit_log_view_details_modal");

    cy.get(".btn-close").click();

    cy.visit("/#/admin/settings");
    cy.get('[data-cy="advanced"]').click();
    cy.get('input[name="node.dataModel.allow_indexing"]').click();
    cy.get("#save").click();

    cy.logout();
  });
});