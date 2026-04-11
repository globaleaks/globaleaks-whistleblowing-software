describe("Admin configure files", () => {
  it("should be able to upload, download and delete files", () => {
    cy.login_admin();

    cy.visit("#/admin/settings");

    cy.get('[data-cy="files"]').click();

    cy.get("[name='authenticationData.session.permissions.can_upload_files']").should("not.be.checked");
    cy.get("[name='authenticationData.session.permissions.can_upload_files_switch']").click();
    cy.get(".modal").should("be.visible");
    cy.get(".modal [type='password']").type("wrongpassword");
    cy.get(".modal .btn-primary").click();

    cy.get(".modal [type='password']", { timeout: 5000 })
      .should('not.have.value') // Check the input is emptied due to the wrong password
      .and('have.value', '');

    cy.get(".modal [type='password']").clear().type(Cypress.env("user_password"));
    cy.get(".modal .btn-primary").click();

    cy.get("[name='authenticationData.session.permissions.can_upload_files']").should("be.checked");

    cy.takeScreenshot("admin/site_settings_files");

    cy.get("div.uploadfile.file-css input[type='file']").selectFile({
      contents: "./cypress/fixtures/files/test.css",
      fileName: "test.css",
      mimeType: "text/css"
    }, {"force": true});

    cy.get("div.file-custom input").selectFile({
      contents: "./cypress/fixtures/files/test.pdf",
      fileName: "test.pdf",
      mimeType: "application/pdf"
    }, {"force": true});

    cy.contains('test.pdf').should('be.visible')

    cy.get("table#fileList").get(".fa-download").last().click();
    cy.get("table#fileList").get(".fa-trash").last().click();

    cy.get("[name='authenticationData.session.permissions.can_upload_files_switch']").click();
    cy.get("[name='authenticationData.session.permissions.can_upload_files']").should("not.be.checked");

    cy.logout();
  });
});
