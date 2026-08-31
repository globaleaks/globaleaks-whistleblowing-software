describe("support conversation", () => {
  // the user that lost its account recovery key asks for the assisted
  // The support function is offered at the interface that asks for the recovery key
  // the administrators reach the interface that lists the requests and
  // send the reset link to the user that issued one.
  it("should allow a user to ask for an assisted recovery and an administrator to send the reset link", () => {
    const request = "I have lost my account recovery key";

    cy.login_receiver();
    cy.get("#SupportLink").click();
    // the New tab exists only once the user has requests: the first time the form is offered
    // directly
    cy.get('[data-cy="support-tab-new"], #support-request-message', {timeout: 20000}).should("be.visible");
    cy.get("body").then($body => {
      if ($body.find('[data-cy="support-tab-new"]').length) {
        cy.get('[data-cy="support-tab-new"]').click();
      }
    });
    cy.get("#support-request-message").should("be.visible").type(request);
    cy.takeScreenshot("user/support_request_form", ".modal-dialog");
    cy.takeScreenshot("user/support_request_form_detail", "#SupportRequest");
    cy.get("#modal-action-ok").click();
    cy.contains(".modal", request).should("be.visible");
    cy.get(".modal #modal-action-cancel").click();
    cy.logout();

    cy.login_admin();
    cy.visit("/#/admin/support");
    cy.get("#AdminSupport").should("be.visible");
    cy.takeScreenshot("admin/support_requests");
    cy.get('#AdminSupport [data-cy="toggle-support-request"]').first().click();
    cy.get('#AdminSupport [data-cy="support-request-details"]').should("be.visible");
    cy.takeScreenshot("admin/support_request_detail", '#AdminSupport [data-cy="support-request-details"]');
    // the request names its author and links to the card of the account
    cy.contains('#AdminSupport [data-cy="support-request-details"]', request)
      .should("be.visible")
      .within(() => {
        cy.get('a[href*="/admin/users"]').click();
      });

    // the card of the account the request came from is the one opened, and the
    // reset link is sent from there
    cy.get("#send_reset_link").should("be.visible");
    cy.takeScreenshot("admin/user_password_actions_detail", ".form-group:has(#send_reset_link)");
    cy.get("#send_reset_link").click();

    // the operation is confirmed with the administrator's own password
    cy.get("[name='secret']").should("be.visible").clear().type(Cypress.env("user_password"));
    cy.intercept("PUT", "/api/admin/config").as("sendResetLink");
    cy.get("#confirm").click();
    cy.wait("@sendResetLink").its("response.statusCode").should("be.within", 200, 299);
    cy.get(".modal").should("not.exist");

    // the request is untouched by the operation and stays in the list: reached from the menu,
    // as a new load would drop the session, once the page has redrawn after the operation
    cy.waitForPageIdle();
    cy.get("#admin_support").should("be.visible").click();
    cy.waitForUrl("/admin/support");
    cy.get('#AdminSupport [data-cy="toggle-support-request"]').first().click();
    cy.contains('#AdminSupport [data-cy="support-request-details"]', request).should("be.visible");
    cy.logout();
  });

  it("should allow a recipient and administrator to exchange messages", () => {
    const request = "Recipient support request";
    const reply = "Administrator support reply";

    cy.login_receiver();
    cy.get("#SupportLink").click();
    // the New tab exists only once the user has requests: the first time the form is offered
    // directly
    cy.get('[data-cy="support-tab-new"], #support-request-message', {timeout: 20000}).should("be.visible");
    cy.get("body").then($body => {
      if ($body.find('[data-cy="support-tab-new"]').length) {
        cy.get('[data-cy="support-tab-new"]').click();
      }
    });
    cy.get("#support-request-message").should("be.visible").type(request);
    cy.get("#modal-action-ok").click();
    cy.contains(".modal", request).should("be.visible");
    cy.get(".modal #modal-action-cancel").click();
    cy.logout();

    cy.login_admin();
    cy.visit("/#/admin/support");
    cy.get('#AdminSupport [data-cy="toggle-support-request"]').first().click();
    cy.contains('#AdminSupport [data-cy="support-request-details"]', request)
      .should("be.visible")
      .within(() => {
        cy.get('textarea[id^="support-reply-"]').type(reply);
        cy.get('[data-cy="send-support-reply"]').click();
      });
    cy.contains("#AdminSupport", reply).should("be.visible");
    cy.logout();

    cy.login_receiver();
    cy.get("#SupportLink").click();
    cy.contains(".modal .config-item", reply).find(".editorTitle").click();
    cy.contains(".modal", reply).should("be.visible");
    cy.get(".modal #modal-action-cancel").click();
    cy.logout();
  });
});
