describe("admin configure mail", () => {
  it("should configure mail", () => {
    cy.login_admin();
    cy.visit("/#/admin/notifications");

    cy.get("[name='notification.dataModel.tip_expiration_threshold']").clear().type("24");

    cy.get("#save_notification").click();

    cy.get('[data-cy="smtp"]').first().click();
    cy.takeScreenshot("admin/notification_settings_smtp1");

    cy.get('#smtp2_enabled').click();
    cy.takeScreenshot("admin/notification_settings_smtp2");

    cy.get("#save_notification").click();
    cy.logout();
  });

  it("should configure SMTP1 and SMTP2 and reset configurations", () => {
    cy.login_admin();
    cy.visit("/#/admin/notifications");
    cy.get('[data-cy="smtp"]').first().click();
    cy.get('#smtp-server-address').clear().type("mail.example.org");
    cy.get('#smtp2-server-address').clear().type("mail.example.org");
    cy.get("#save_notification").click();
    cy.get("#reset_smtp1").click();
    cy.get("#reset_smtp2").click();
    cy.get("#save_notification").click();
    cy.logout();
  });

  it("should test SMTP configurations", () => {
    cy.login_admin();
    cy.visit("/#/admin/notifications");
    cy.get('[data-cy="smtp"]').first().click();
    cy.get('#test_smtp1').click();
    cy.get('input[name="to_mail_address"]').clear().type('test@example.com');
    cy.takeScreenshot("admin/notification_settings_test1");
    cy.get('#confirm').click();
    cy.wait(1000);
    cy.get('#test_smtp2').click();
    cy.get('input[name="to_mail_address"]').clear().type('test@example.com');
    cy.takeScreenshot("admin/notification_settings_test2");
    cy.get('#confirm').click();
    cy.wait(1000);
    cy.logout();
  });
});
