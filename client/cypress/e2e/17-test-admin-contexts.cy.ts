describe("admin configure, add, and delete channels", () => {
  it("should configure an existing channel", () => {
    cy.visit("/");
    cy.login_admin();

    cy.visit("#/admin/channels");

    cy.get("#context-0").within(() => {
      cy.get("#edit_context").click();

      for (let i = 0; i <= 2; i++) {
        cy.get(".add-receiver-btn").click();
        cy.get('ng-select[name="selected.value"]').click();
        if (i === 0) {
          cy.get('ng-select[name="selected.value"]').contains('Recipient').click();
        } else {
          cy.get('ng-select[name="selected.value"]').contains(`Recipient${i + 1}`).click();
        }
      }

      cy.get("#advance_context").click();
      cy.get("#save_context").click();
    });
  });

  it("should add new channels", () => {
    cy.visit("/");
    cy.login_admin();

    cy.visit("#/admin/channels");
    const add_context = async (context_name: string) => {
      cy.get(".show-add-context-btn").click();
      cy.get("[name='new_context.name']").type(context_name);
      cy.get("#add-btn").click();
      cy.contains(context_name, { timeout: 10000 }).should("be.visible");
    };

    add_context("Topic A");
    add_context("Topic B");
    add_context("Topic C");
  });

  it("should delete existing channels", () => {
    cy.visit("/");
    cy.login_admin();

    cy.visit("#/admin/channels");
    cy.get("[name='delete_context']").last().click();
    cy.get("#modal-action-ok").click();

    cy.logout();
  });

  it("should add/remove new status and sub-status in the admin section", () => {
    cy.login_admin();

    cy.visit("/#/admin/casemanagement");
    cy.get(".config-section").should("be.visible");
    cy.get(".show-add-user-btn").click();
    cy.get(".addSubmissionStatus").should("be.visible");
    cy.get('input[name="name"]').type("Test");
    cy.get("#add-btn").click();
    cy.get(".config-section").contains("Test").should("be.visible").click();
    cy.get("#add-sub-status").click();
    cy.get('input[name="label"]').type("closed 1");
    cy.get("#add-submission-sub-status").click();
    cy.get("#add-sub-status").click();
    cy.get('input[name="label"]').type("closed 2");
    cy.get("#add-submission-sub-status").click();
    cy.get('#move-up-button').click();
    cy.get('#move-down-button').click();
    cy.get('#substatus-edit-button').first().click();
    cy.get('input[name="substatus.label"]').clear();
    cy.get('input[name="substatus.label"]').type('Test Label').should('have.value', 'Test Label');
    cy.get('select[name="substatus.tip_timetolive_option"]').select(1);
    cy.get('input[name="substatus.tip_timetolive"]').clear();
    const inputValue = 10;
    cy.get('input[name="substatus.tip_timetolive"]').type(inputValue.toString()).should('have.value', inputValue.toString());
    cy.get('#substatus-save-button').first().click();
    cy.get('#substatus-delete-button').first().click();
    cy.get("#modal-action-ok").click();
    cy.get('#substatus-delete-button').first().click();
    cy.get("#modal-action-ok").click();
    cy.get("#delete-submissions-status").last().click();
    cy.get("#modal-action-ok").click();
   
    cy.get(".show-add-user-btn").click();
    cy.get(".addSubmissionStatus").should("be.visible");
    cy.get('input[name="name"]').type("Partial");
    cy.get("#add-btn").click();
    cy.get(".config-section").contains("Partial").should("be.visible").click();
    cy.get("#add-sub-status").click();
    cy.get('input[name="label"]').type("closed");
    cy.get("#add-submission-sub-status").click();

    cy.logout();
  });
});
