describe('add, configure, delete external organization', () => {

  // it('request eo accreditation', () => {    
  //   cy.request_external_organization();
  // });

  it('accept affiliated eo request', () => {

    cy.request_external_organization("Affiliated OE", "examplepec@examplepec.com", "exampleurl.com", "CRSLNS80D01F839B");
    cy.wait(6000);

    cy.login_accreditor();

    cy.visit("/#/accreditor/organizations");

    cy.get("#req-0").first().click();

    cy.get("#organization-button").click();

    cy.get("#accept-button").click();

  });

  it('reject eo request', () => {

    cy.request_external_organization("OE_to_reject", "examplepec1@examplepec.com", "exampleurl.com", "CRSLNS80D01F839B");

    cy.wait(6000);

    cy.login_accreditor();

    cy.visit("/#/accreditor/organizations");

    cy.get("#req-0").first().click();

    cy.get("#reject-button").click();

    cy.get("#textarea").type("example delete message");

    cy.get("#modal-action-ok").click();

  });

  it('accred not affiliated eo request', () => {

    cy.request_external_organization("Not Affiliated OE", "examplepec2@examplepec.com", "exampleurl.com", "CRSLNS80D01F839B");

    cy.login_accreditor();

    cy.visit("/#/accreditor/organizations");

    cy.get("#req-0").first().click();

    cy.get("#accept-button").click();

    cy.url().then((currentUrl) => {
      const index = currentUrl.split("/").length - 1;
      const reqId = currentUrl.split("/")[index];

      cy.logout();
      cy.confirm_accreditation_request(reqId);

    });     
  });

})