describe("admin add, configure and delete questionnaires", () => {
  const add_questionnaires = async (questionnaire_name: string) => {
    cy.get(".show-add-questionnaire-btn").click();
    cy.get("input[name='new_questionnaire.name']").type(questionnaire_name);
    cy.get("#add-questionnaire-btn").click();
    cy.contains(questionnaire_name).should("be.visible");
  };

  const add_question = async (question_type: string, question_id: number) => {
    cy.get(".show-add-question-btn").first().click();
    cy.get("input[name='new_field.label']").first().type(question_type);
    cy.get("select[name='new_field.type']").first().select(question_id);
    cy.get("#add-field-btn").first().click();

    if (["Checkbox", "Selection box"].indexOf(question_type) === 0) {
      cy.get('.fieldBox').should('be.visible');
      cy.contains('span', question_type).as('questionType').should('be.visible');
      cy.get('@questionType').click();

      for (let i = 0; i < 3; i++) {
        cy.get('button[name="addOption"]').click();
        cy.get("input[name='option.label']").eq(i).type("option");

        if (i === 0) {
          cy.get('#option_hint').first().click();
          cy.get('#hint1').type('This is hint 1');
          cy.get('#hint2').type('This is hint 2');
          cy.get('#modal-action-ok').click();

          cy.get('#option_block_submission').first().click();

          cy.get('#option_trigger_receiver').first().click();
          cy.get('[data-cy="receiver_selection"]').click();
          cy.get('.ng-option').eq(0).click();
          cy.get('#modal-action-ok').click();

          cy.get('#option_score').first().click();
          cy.get('select.form-control').select('multiplier');
          cy.get('#score_points').clear().type('5');
          cy.get('#modal-action-ok').click();
        }
      }

      cy.get('button[name="delOption"]').eq(2).click();
      cy.get('button[name="save_field"]').filter(':visible').first().click();
    }
  };

  const add_step = async (step_label: string) => {
    cy.get("button[name='new_step']").click();
    cy.get("input[name='new_step.label']").type(step_label);
    cy.get("#add-step-btn").click();
    cy.contains(step_label).should("be.visible");
  };

  it("should add and configure questionnaires", () => {
    cy.login_admin();
    cy.visit("/#/admin/questionnaires");

    add_questionnaires("Questionnaire 1");
    add_questionnaires("Questionnaire 2");

    cy.contains("Questionnaire 1").click();

    add_step("Step 1");
    add_step("Step 2");
    add_step("Step 3");

    const fieldTypes = Cypress.env("field_types");
    cy.contains("Step 2").should('be.visible').click();

    fieldTypes.forEach((questionType: string, index: number) => {
      add_question(questionType, index);
    });

    cy.contains("Step 2").click();

    cy.get('button[name="delStep"]').eq(2).click();
    cy.get("#modal-action-ok").click();

    cy.contains("Questionnaire 1").click();

    cy.get('button[name="deleteQuestionnaire"]').each(($button) => {
      cy.wrap($button).click();
      cy.get("#modal-action-ok").click();
    });

    cy.get('[data-cy="question_templates"]').click();

    fieldTypes.forEach((questionType: string, index: number) => {
      add_question(questionType, index);
    });

    cy.get(".fa-file-export").last().click();

    cy.logout();
  });

  it("should import custom questionnaire file", () => {
    cy.login_admin();

    cy.visit("/#/admin/questionnaires");
    cy.get("#keyUpload").click();
    cy.fixture("questionnaires/questionnaire1.txt").then(fileContent => {
      cy.get('input[type="file"]').then(input => {
        const blob = new Blob([fileContent], { type: "text/plain" });
        const testFile = new File([blob], "questionnaires/questionnaire1.txt");
        const dataTransfer = new DataTransfer();
        dataTransfer.items.add(testFile);
        const inputElement = input[0] as HTMLInputElement;
        inputElement.files = dataTransfer.files;

        const changeEvent = new Event("change", { bubbles: true });
        input[0].dispatchEvent(changeEvent);
      });

    });
    cy.fixture("questionnaires/questionnaire2.txt").then(fileContent => {
      cy.get('input[type="file"]').then(input => {
        const blob = new Blob([fileContent], { type: "text/plain" });
        const testFile = new File([blob], "questionnaires/questionnaire2.txt");
        const dataTransfer = new DataTransfer();
        dataTransfer.items.add(testFile);
        const inputElement = input[0] as HTMLInputElement;
        inputElement.files = dataTransfer.files;

        const changeEvent = new Event("change", { bubbles: true });
        input[0].dispatchEvent(changeEvent);
      });

    });
    cy.get("#questionnaire-2").should("be.visible");
    cy.logout();
  });

  it("should add duplicate questionnaire", function () {
    cy.login_admin();
    cy.visit("/#/admin/questionnaires");
    cy.get(".fa-clone").first().click();
    cy.get('input[name="name"]').type("duplicate questionnaire");
    cy.get("#modal-action-ok").click();
    cy.logout();
  });

  it("should export questionnaire", function () {
    cy.login_admin();
    cy.visit("/#/admin/questionnaires");
    cy.get(".fa-file-export").first().click();
    cy.logout();
  });
});
