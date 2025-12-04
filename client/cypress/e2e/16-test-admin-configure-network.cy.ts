describe("admin configure network", () => {
  beforeEach(() => {
    cy.login_admin();
    cy.visit("/#/admin/network");
  });

  it("should be able to configure https", () => {
    cy.get('[data-cy="https"]').should('be.visible').click();

    cy.get('[name="hostname"]').clear().type("127.0.0.1");
    cy.get('#save_hostname').click();

    cy.get("#HTTPSManualMode").click();
    cy.get("#pkGen").should('be.visible').click();
    cy.get("#csrGen").click();
    cy.get('[name="country"]').type("IT");
    cy.get('[name="province"]').type("Milano");
    cy.get('[name="city"]').type("Lombardia");
    cy.get('[name="company"]').type("GlobaLeaks");
    cy.get('[name="email"]').type("admin@globaleaks.org");
    cy.get("#csrSubmit").click();

    cy.get("#deleteKey").click();
    cy.get("#modal-action-ok").should('be.visible').click();
    cy.get("#deleteKey").should("not.exist");
    cy.get("#HTTPSManualMode").should('be.visible').click();

    cy.get("div.card.key input[type=file]").selectFile({
      contents: "../backend/globaleaks/tests/data/https/valid/key.pem",
      fileName: "key.pem",
      mimeType: "application/x-pem-file"
    }, {"force": true});
    cy.get("#deleteKey").should('be.visible')

    cy.get("div.card.cert input[type=file]").selectFile({
      contents: "../backend/globaleaks/tests/data/https/valid/cert.pem",
      fileName: "cert.pem",
      mimeType: "application/x-pem-file"
    }, {"force": true});
    cy.get("#deleteCert").should('be.visible')

    cy.get("div.card.chain input[type=file]").selectFile({
      contents: "../backend/globaleaks/tests/data/https/valid/chain.pem",
      fileName: "chain.pem"
    }, {"force": true});

    cy.get("#deleteChain").should('be.visible')
    cy.get("#deleteChain").click();
    cy.get("#modal-action-ok").click();

    cy.get("#deleteCert").click();
    cy.get("#modal-action-ok").click();

    cy.get("#deleteKey").should('be.visible').click();
    cy.get("#modal-action-ok").click();
    cy.logout();
  });

  it("should configure url redirects", () => {
    cy.get('[data-cy="url_redirects"]').first().click();
    for (let i = 0; i < 3; i++) {
      cy.get('[name="path1"]').type(`yyyyyyyy-${i}`);
      cy.get('[name="path2"]').type("xxxxxxxx");
      cy.get("#add_redirect").click();
      cy.get("#delete_redirect").first().click();
    }
    cy.logout();
  });
});
