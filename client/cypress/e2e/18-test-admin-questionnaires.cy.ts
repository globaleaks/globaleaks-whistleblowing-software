import {t} from "../support/i18n";
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

      cy.get('[data-cy="import-options"]').click();

      cy.fixture("questionnaires/options_import.txt").then((fileContent) => {
        cy.get('input[type="file"]').last().then((input) => {
          const blob = new Blob([fileContent], { type: "text/plain" });
          const testFile = new File([blob], "options_import.txt");
          const dataTransfer = new DataTransfer();
          dataTransfer.items.add(testFile);
          const inputElement = input[0] as HTMLInputElement;
          inputElement.files = dataTransfer.files;

          const changeEvent = new Event("change", { bubbles: true });
          input[0]!.dispatchEvent(changeEvent);
        });
      });

      cy.get('button[name="delOption"]').eq(2).click();
      cy.get(".field [data-action='save']").filter(':visible').first().click();
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
    cy.contains("Step 2").click();

    fieldTypes.forEach((questionType: string, index: number) => {
      add_question(questionType, index);
    });

    cy.contains("Step 2").click();

    cy.get(".step [data-action='delete']").eq(2).click();
    cy.get("#modal-action-ok").click();

    cy.contains("Questionnaire 1").click();

    cy.get(".questionnaire [data-action='delete']").each(($button) => {
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

  // Every property a question offers is written through its editor: each type of question template
  // is opened, its properties are filled and saved
  it("should edit the properties of every type of question", () => {
    cy.login_admin();
    cy.visit("/#/admin/questionnaires");
    cy.get('[data-cy="question_templates"]').click();

    // The box of the template whose title is exactly the label, opened for editing
    const edit = (label: string, fn: () => void) => {
      cy.get(".fieldBox").filter((_, el) => {
        const title = el.querySelector(".editorHeader [role='button'] > span");
        return title !== null && (title.textContent || "").trim() === label;
      }).first().as("box");
      cy.get("@box").find(".editorHeader [role='button']").first().click();
      cy.get("@box").find("[data-action='save']").should("be.visible");
      cy.get("@box").within(fn);
      cy.get("@box").find("[data-action='save']").first().click();
      cy.get("@box").find("[data-action='save']").should("not.exist");
    };

    const tick = (label: string) => {
      cy.contains(".form-group", label).find("input[type='checkbox']").first().check({force: true});
    };

    const pickADay = (which: "first" | "last") => {
      cy.get("ngb-datepicker .ngb-dp-day:not(.disabled):not(.hidden)")[which]().click();
    };

    edit("Single-line text input", () => {
      cy.get("input[id^='field-hint-']").clear().type("A hint");
      cy.get("textarea[id^='field-description-']").clear().type("A description");
      cy.get("input[id^='field-placeholder-']").clear().type("A placeholder");
      tick("Mandatory");
      tick("Preview");
      cy.get("input[id^='field-width-']").clear().type("6");
      cy.get("input[id^='field-min-len-']").clear().type("1");
      cy.get("input[id^='field-max-len-']").clear().type("100");
    });

    edit("Multi-line text input", () => {
      cy.get("select[id^='field-type-']").select("textarea");
    });

    edit("Selection box", () => {
      tick("Display options alphabetically");
      cy.get("button[name='addOption']").click();
      cy.get("button[name='addOption']").click();
      cy.get("input[name='option.label']").eq(0).type("Second");
      cy.get("input[name='option.label']").eq(1).type("First");
      cy.get(".field-option").eq(1).find(".fa-chevron-up").click();
      cy.get(".field-option").eq(0).find(".fa-chevron-down").click();
      cy.get("input[name='option.label']").eq(0).should("have.value", "Second");
    });

    edit("Multiple choice input", () => {
      cy.get("select[id^='field-type-multi-']").select("multichoice");
      tick("Include in statistical reports");
    });

    edit("Attachment", () => {
      tick("Accept multiple file uploads");
    });

    edit("Terms of service", () => {
      cy.get("textarea[id^='field-tos-text-']").clear().type("The terms");
      cy.get("input[id^='field-checkbox-label-']").clear().type("I agree");
      tick("Attachment");
      cy.get("input[id^='field-attachment-text-']").clear().type("The policy");
      cy.get("input[id^='field-attachment-url-']").clear().type("https://example.org/policy");
    });

    edit("Date", () => {
      cy.get("input[id^='field-min-date-']").siblings("button").first().click();
      pickADay("first");
      cy.get("input[id^='field-min-date-']").siblings("span").find("button").click();
      cy.get("input[id^='field-max-date-']").siblings("button").first().click();
      pickADay("last");
    });

    edit("Voice", () => {
      cy.get("input[id^='field-max-len-']").clear().type("120");
    });

    edit("Group of questions", () => {
      tick("Accept multiple answers");
      tick("Add multimedia content");
      cy.get("select[id^='field-multimedia-type-']").select("video");
      cy.get("input[id^='field-multimedia-url-']").clear().type("https://example.org/video.mp4");

      cy.contains("button", "Add new question").click();
      cy.get("input[name='new_field.label']").first().type("Inner question");
      cy.get("select[name='new_field.type']").first().select(t("Single-line text input"));
      cy.get("#add-field-btn").first().click();
      cy.contains(".fieldBox", "Inner question").should("be.visible");

      cy.contains("button", "Add question from template").click();
      // the list of the templates is rendered with translate, unlike the title of the box
      cy.get("#field-template-select").select(t("Single-line text input"));
      cy.get(".add-field-from-template #add-field-btn").click();

      // The questions of the group move around one another
      cy.get(".fieldBox [data-action='move-down']").first().click();
      cy.get(".fieldBox [data-action='move-up']").first().click();
      cy.get(".fieldBox [data-action='move-right']").first().click();
      cy.get(".fieldBox [data-action='move-left']").first().click();
      cy.get(".fieldBox [data-action='export']").first().click();
    });

    cy.logout();
  });

  // The steps of a questionnaire are described, ordered and shown upon a given answer
  it("should edit the steps of a questionnaire", () => {
    cy.login_admin();
    cy.visit("/#/admin/questionnaires");

    add_questionnaires("Questionnaire 3");
    cy.contains("Questionnaire 3").click();
    add_step("First step");
    add_step("Second step");

    cy.contains("First step").click();
    add_question("Checkbox", 4);

    cy.contains(".step", "Second step").as("step");
    cy.get("@step").find(".editorHeader [role='button']").first().click();
    cy.get("@step").within(() => {
      cy.get("textarea[id^='step-description-']").clear().type("The second step of the questionnaire");
      cy.get("[data-action='save']").click();
    });

    // the steps swap places on request
    cy.get("@step").find("[data-action='move-up']").click();
    cy.get(".step").first().should("contain", "Second step");
    cy.get(".step").first().find("[data-action='move-down']").click();
    cy.get(".step").first().should("contain", "First step");

    cy.contains("Questionnaire 3").click();
    cy.get(".questionnaire [data-action='delete']").last().click();
    cy.get("#modal-action-ok").click();
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
        input[0]!.dispatchEvent(changeEvent);
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
        input[0]!.dispatchEvent(changeEvent);
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

  // The statistical mark is offered on the question templates with closed answers
  it("should mark a question template for the statistical reports", function () {
    cy.login_admin();
    cy.visit("/#/admin/questionnaires");
    cy.get('[data-cy="question_templates"]').click();

    cy.get(".show-add-question-btn").first().click();
    cy.get("input[name='new_field.label']").first().type("Statistical question");
    cy.get("select[name='new_field.type']").first().select("Selection box");
    cy.get("#add-field-btn").first().click();

    cy.contains(".fieldBox span", "Statistical question").click();
    cy.contains(".fieldBox .form-group", "Include in statistical reports").should("be.visible");
    cy.takeScreenshot("admin/question_statistical_detail", '.fieldBox:contains("Statistical question")');

    cy.logout();
  });
});
