describe("recipient admin tip actions", () => {
  it("should close and reopen reports", function () {
    cy.login_receiver();

    cy.visit("/#/recipient/reports");
    cy.get("#tip-0").first().click();

    cy.get("#tip-action-change-status").click();
    cy.get('#assignSubmissionStatus').select(2);
    cy.get('textarea[name="reason"]').type("This is a close status test motivation");
    cy.get("#modal-action-ok").click();
    cy.get("#tip-action-reopen-status").click();
    cy.get('textarea[name="motivation"]').type("This is a reopen status test motivation");
    cy.get("#modal-action-ok").click();

    cy.logout();
  });

  it("recipient should file a report on behalf of whistleblower", function () {
    cy.login_receiver();

    cy.visit("/#/recipient/reports");
    cy.get("#tip-action-open-new-tab").click();
    cy.visit("/#/recipient/reports");

    cy.logout();
  });

  it("should set a postpone date for reports", function () {
    cy.login_receiver();
    cy.visit("/#/recipient/reports");
    cy.get("#tip-0").first().click();
    cy.get("#tip-action-postpone").click();
    cy.get('.modal').should('be.visible');
    cy.get('input[name="dp"]').invoke('val').then((currentDate: any) => {

      const current = new Date(currentDate);
      const nextDay = new Date(current);
      nextDay.setDate(nextDay.getDate() + 1);
      cy.get('input[name="dp"]').click();
      let day: number
      if (nextDay.getDate() < 10) {
        day = 10
      } else {
        day = nextDay.getDate()
      }
      cy.get('.btn-link[aria-label="Next month"]').click();
      cy.get('.ngb-dp-day').contains(day).click();
    });
    cy.get('#modal-action-ok').click();
    cy.logout();
  });

  it("should set a reminder date for reports", function () {
    cy.login_receiver();

    cy.visit("/#/recipient/reports");
    cy.get("#tip-0").first().click();
    cy.get("#tip-action-reminder").click();
    cy.get('.modal').should('be.visible');

    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    const formattedDate = tomorrow.toISOString().split('T')[0];

    cy.get('input[name="dp"]').click().clear();
    cy.get('input[name="dp"]').click().type(formattedDate);
    cy.get('#modal-action-ok').click();

    cy.logout();
  });


  it("should change sub-status for reports", function () {
    cy.login_receiver();
    cy.visit("/#/recipient/reports");
    cy.get("#tip-0").first().click();
    cy.get("#tip-action-change-status").click();
    cy.get('#assignSubmissionStatus').select(1);
    cy.get('textarea[name="reason"]').type("This is a test motivation");
    cy.get("#modal-action-ok").click();
    cy.logout();
  });

  it("should upload, download and delete a file", function () {
    cy.login_receiver();
    cy.visit("/#/recipient/reports");
    cy.get("#tip-0").first().click();
    cy.get('#upload_description').type("description");
    cy.get('i.fa-solid.fa-upload').click();
    cy.fixture("files/test.txt").then(fileContent => {
      cy.get('input[type="file"]').then(input => {
        const blob = new Blob([fileContent], { type: "text/plain" });
        const testFile = new File([blob], "files/test.txt");
        const dataTransfer = new DataTransfer();
        dataTransfer.items.add(testFile);
        const inputElement = input[0] as HTMLInputElement;
        inputElement.files = dataTransfer.files;

        const changeEvent = new Event("change", { bubbles: true });
        input[0].dispatchEvent(changeEvent);
      });
    });

    cy.get('.download-button').should('be.visible');
    cy.get('.download-button').first().click();
    cy.get('.fa-trash').first().click();
    cy.get("#modal-action-ok").click();

    cy.logout();
  });

  it("should check multiple filter of report", function () {
    cy.login_receiver();

    cy.visit("/#/recipient/reports");

    cy.get('span#SearchFilter input[type="text"]').type("your search term");
    cy.get('span#SearchFilter input[type="text"]').clear();

    cy.get('th.TipInfoID').click();

    cy.get('th.TipInfoContext i.fa-solid.fa-filter').click();
    cy.get('.multiselect-item-checkbox').eq(1).click();
    cy.get('.multiselect-item-checkbox').eq(0).click();

    cy.get('.TipInfoSubmissionDate .fas.fa-calendar').click();
    cy.get('.custom-day').first().click();
    cy.get('.custom-day').eq(4).click({ shiftKey: true });
    cy.contains('button.btn.btn-danger', 'Reset').click();

    cy.logout();
  });

  it("should apply grant and revoke access to selected reports for a specific recipient", function () {
    cy.login_receiver();

    cy.visit("/#/recipient/reports");
    cy.get('#tip-action-select-all').click();
    cy.get('#tip-action-revoke-access-selected').click();
    cy.get('[data-cy="receiver_selection"]').click();
    cy.get('.ng-dropdown-panel').should('be.visible');
    cy.get('[data-cy="receiver_selection"]').click();
    cy.contains('.ng-option', 'Recipient2').click();
    cy.get("#modal-action-ok").click();

    cy.get('#tip-action-reload').click();

    cy.get('#tip-action-select-all').click();
    cy.get("#tip-action-grant-access-selected").click();
    cy.get('[data-cy="receiver_selection"]').click();
    cy.get('.ng-dropdown-panel').should('be.visible');
    cy.get('[data-cy="receiver_selection"]').click();
    cy.contains('.ng-option', 'Recipient2').click();
    cy.get("#modal-action-ok").click();
    cy.logout();
  });

  it("should revoke report access to Recipient2", function () {
    cy.login_receiver();
    cy.visit("/#/recipient/reports");
    cy.get("#tip-0").first().click();
    cy.get("#tip-action-revoke-access").should('be.visible').click();
    cy.get('[data-cy="receiver_selection"]').click();
    cy.get('.ng-dropdown-panel').should('be.visible');
    cy.get('[data-cy="receiver_selection"]').click();
    cy.contains('.ng-option', 'Recipient2').click();
    cy.get("#modal-action-ok").click();
    cy.logout();
  });

  it("should revoke report access to Recipient3", function () {
    cy.login_receiver();
    cy.visit("/#/recipient/reports");
    cy.get("#tip-0").first().click();
    cy.get("#tip-action-revoke-access").should('be.visible').click();
    cy.get('[data-cy="receiver_selection"]').click();
    cy.get('.ng-dropdown-panel').should('be.visible');
    cy.get('[data-cy="receiver_selection"]').click();
    cy.contains('.ng-option', 'Recipient3').click();
    cy.get("#modal-action-ok").click();
    cy.logout();
  });

  it("should grant report access to Recipient2", function () {
    cy.login_receiver();
    cy.visit("/#/recipient/reports");
    cy.get("#tip-0").first().click();
    cy.get("#tip-action-grant-access").should('be.visible').click();
    cy.get('[data-cy="receiver_selection"]').click();
    cy.get('.ng-dropdown-panel').should('be.visible');
    cy.get('[data-cy="receiver_selection"]').click();
    cy.contains('.ng-option', 'Recipient2').click();
    cy.get("#modal-action-ok").click();
    cy.logout();
  });

  it("should transfer report access to Recipient3", function () {
    cy.login_receiver();
    cy.visit("/#/recipient/reports");
    cy.get("#tip-0").first().click();
    cy.get("#tip-action-transfer-access").should('be.visible').click();
    cy.get('[data-cy="receiver_selection"]').click();
    cy.get('.ng-dropdown-panel').should('be.visible');
    cy.get('[data-cy="receiver_selection"]').click();
    cy.contains('.ng-option', 'Recipient3').click();
    cy.get("#modal-action-ok").click();
    cy.logout();
  });
});
