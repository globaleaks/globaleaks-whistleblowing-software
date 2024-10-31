describe("admin configure mail", () => {
  it("should configure mail", () => {
    cy.login_admin();
    cy.visit("/#/admin/notifications");

    cy.get("[name='notification.dataModel.tip_expiration_threshold']").clear().type("24");

    cy.get("#save_notification").click();

    cy.logout();
  });
});
