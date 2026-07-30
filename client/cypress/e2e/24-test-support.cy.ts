describe("support conversation", () => {
  it("should allow a recipient and administrator to exchange messages", () => {
    const request = "Recipient support request";
    const reply = "Administrator support reply";

    cy.login_receiver();
    cy.get("#SupportLink").click();
    cy.get("#support-request-message").type(request);
    cy.get("#modal-action-ok").click();
    cy.contains(".modal", request).should("be.visible");
    cy.get(".modal #modal-action-cancel").click();
    cy.logout();

    cy.login_admin();
    cy.visit("/#/admin/support");
    cy.contains("#AdminSupport .config-item", request)
      .should("be.visible")
      .within(() => {
        cy.get(".editorHeader").click();
        cy.get('textarea[id^="support-reply-"]').type(reply);
        cy.get('[data-cy="send-support-reply"]').click();
      });
    cy.contains("#AdminSupport", reply).should("be.visible");
    cy.logout();

    cy.login_receiver();
    cy.get("#SupportLink").click();
    cy.contains(".modal .nav-link", "My support requests").click();
    cy.contains(".modal .config-item", reply).should("be.visible").find(".editorHeader").click();
    cy.contains(".modal", reply).should("be.visible");
    cy.get(".modal #modal-action-cancel").click();
    cy.logout();
  });
});
