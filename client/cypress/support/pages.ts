class WhistleblowerPage {
  public static performSubmission(arg?:string) {
    cy.visit("#/");
    cy.takeScreenshot("whistleblower/home");

    cy.get("#WhistleblowingButton").click();
    cy.get("#step-0").should("be.visible");

    cy.get("#step-0-field-0-0-input-0").type("summary");
    cy.get("#step-0-field-1-0-input-0").type("detail");
    cy.get("#step-0-field-2-0-input-0").type("...");
    cy.get("#step-0-field-2-1-input-0").type("...");


    cy.get("#step-0-field-3-0-input-0").first().select("13d17a19-1c7c-482c-9e6c-16896f0d5f1b");
    cy.get("#step-0-field-4-0-input-0").first().select(1);

    cy.get("#step-0-field-6-0-input-0").type("...");

    if(arg && arg =="single_file_upload"){
      cy.get("#step-0-field-5-0-input-0 input[type='file']").selectFile({
        contents: "./cypress/fixtures/files/test.pdf",
        fileName: "test.pdf",
        mimeType: "application/pdf"
      }, {"force": true});
      
    } else {
      cy.get("#step-0-field-5-0-input-0 input[type='file']").selectFile({
        contents: "./cypress/fixtures/files/test.pdf",
        fileName: "test.pdf",
        mimeType: "application/pdf"
      }, {"force": true});
  
      cy.get("#step-0-field-5-0-input-0 input[type='file']").selectFile({
        contents: "./cypress/fixtures/files/test.zip",
        fileName: "test.zip",
        mimeType: "application/zip"
      }, {"force": true});
    }

    cy.get("#step-0-field-7-0-input-0").first().select(2);

    cy.get("#step-0-field-10-0-input-0").type("...");
    cy.wait(1000);
    cy.get("#SubmitButton").should("be.visible");

    cy.takeScreenshot("whistleblower/submission");

    cy.get("#SubmitButton").click();

    cy.get("#ReceiptCode").should("be.visible");

    cy.takeScreenshot("whistleblower/receipt");

    return cy.get('#ReceiptCode').invoke('val').then((value) => {
      return value;
    });
  }
}

export { WhistleblowerPage };
