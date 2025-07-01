describe("admin configure mail", () => {
  it("should configure mail", () => {
    cy.login_admin();
    cy.visit("/#/admin/notifications");

    cy.get("[name='notification.dataModel.tip_expiration_threshold']").clear().type("24");

    cy.get("#save_notification").click();

    cy.logout();
  });

  it("should enable secondary SMTP", () => {
    cy.login_admin();
    cy.visit("/#/admin/notifications");

    cy.get('#smtp2_enabled').click();

    cy.get("#save_notification").click();
    cy.logout();
  });

  it("should test SMTP (primary) configuration", () => {
    cy.login_admin();
    cy.visit("/#/admin/notifications");

    cy.get('#test_mail').click();

    cy.get('input[name="to_mail_address"]').clear().type('testuser@example.com');

    cy.get('#confirm').click();
    cy.wait(1000);

    cy.logout();
  });

  it("should test SMTP (secondary) configuration", () => {
    cy.login_admin();
    cy.visit("/#/admin/notifications");

    cy.get('[data-cy="smtp2"]').click();

    cy.get('#test_mail').click();

    cy.get('input[name="to_mail_address"]').clear().type('testuser@example.com');

    cy.get('#confirm').click();
    cy.wait(1000);

    cy.logout();
  });
});