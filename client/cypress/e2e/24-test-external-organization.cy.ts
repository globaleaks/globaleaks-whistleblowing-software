describe('add, configure, delete external organization', () => {

  it('Accept not affiliated EO request', () => {

    cy.request_external_organization("Not Affiliated OE", "examplepec@examplepec.com", "exampleurl.com", "CRSLNS80D01F839B");

    cy.login_accreditor();

    cy.visit("/#/accreditor/organizations");

    cy.get("#req-0").first().click();
    cy.get("#organization-button").click();

    cy.get("#accept-button").click();

  });

  it('reject EO request', () => {

    cy.request_external_organization("OE_to_reject", "examplepec1@examplepec.com", "exampleurl.com", "CRSLNS80D01F839B");

    cy.login_accreditor();

    cy.visit("/#/accreditor/organizations");
    cy.get("#req-0").first().click();

    cy.get("#reject-button").click();

    cy.get(".modal").should("be.visible");
    cy.get("#textarea").type("example delete message");   
    cy.get("#modal-action-ok").click();

  });

  it('accreditation of affiliated EO request', () => {

    cy.request_external_organization("Accredited OE", "examplepec2@examplepec.com", "exampleurl.com", "CRSLNS80D01F839B");

    cy.login_accreditor();

    cy.visit("/#/accreditor/organizations");
    cy.get("#req-0").first().click();

    cy.get("#affiliatedButton").click();

    cy.wait(2000);

    cy.get("#accept-button").click();

    cy.url().then((currentUrl) => {
      const index = currentUrl.split("/").length - 1;
      const reqId = currentUrl.split("/")[index];

      cy.logout();
      cy.confirm_accreditation_request(reqId);

    });     
  });

  it('suspend and reactivate accredited EO', () => {

    cy.login_accreditor();

    cy.visit("/#/accreditor/organizations");
    cy.get("#req-0").first().click();

    cy.get("#org-action-suspend").click();

    cy.wait(2000);

    cy.get("#org-action-reactivate").click();
  });


  it('delete accredited EO', () => {

    cy.request_external_organization("OE_to_delete", "examplepec3@examplepec.com", "exampleurl.com", "CRSLNS80D01F839B");

    cy.login_accreditor();

    cy.visit("/#/accreditor/organizations");
    cy.get("#req-0").first().click();

    cy.get("#affiliatedButton").click();

    cy.wait(2000);

    cy.get("#accept-button").click();

    cy.url().then((currentUrl) => {
      const index = currentUrl.split("/").length - 1;
      const reqId = currentUrl.split("/")[index];

      cy.logout();
      cy.confirm_accreditation_request(reqId);

      cy.wait(2000);

      cy.login_accreditor();

      cy.visit("/#/accreditor/organizations");
      cy.get("#req-0").first().click();

      cy.get("#org-action-delete").click();

      cy.get(".modal").should("be.visible");
      cy.get("#textarea").type("example delete message");   
      cy.get("#modal-action-ok").click();

    });     
  });

})