import {t} from "../support/i18n";
// A questionnaire made of every type of question: the administrator imports it and puts it on the
// channel, the whistleblower answers each question, the recipients read every answer
describe("every type of question is asked, answered and read", () => {
  const importQuestionnaire = (fixture: string) => {
    cy.get("#keyUpload").click();
    cy.fixture(fixture).then(fileContent => {
      cy.get('input[type="file"]').then(input => {
        const blob = new Blob([fileContent], {type: "text/plain"});
        const dataTransfer = new DataTransfer();
        dataTransfer.items.add(new File([blob], fixture));
        (input[0] as HTMLInputElement).files = dataTransfer.files;
        input[0].dispatchEvent(new Event("change", {bubbles: true}));
      });
    });
  };

  const putQuestionnaireOnTheChannel = (name: string) => {
    cy.visit("#/admin/channels");
    cy.get("#context-0").within(() => {
      cy.get("[data-action='edit']").click();
      cy.get("#context-questionnaire-select").select(name);
      cy.intercept("PUT", "**/api/admin/contexts/*").as("saveContext");
      cy.get("[data-action='save']").click();
    });
    cy.wait("@saveContext").its("response.statusCode").should("be.within", 200, 299);
  };

  const pickADay = (toggle: Cypress.Chainable, which: "first" | "last") => {
    toggle.click();
    cy.get("ngb-datepicker .ngb-dp-day:not(.disabled):not(.hidden)")[which]().click();
  };

  it("should import the questionnaire and put it on the channel", () => {
    cy.login_admin();
    cy.visit("/#/admin/questionnaires");
    importQuestionnaire("questionnaires/every-question.txt");
    cy.contains("Every question").should("be.visible");
    cy.takeScreenshot("admin/questionnaire_every_question_detail", "form:contains('Every question')");

    putQuestionnaireOnTheChannel("Every question");
    cy.logout();
  });

  it("should let the whistleblower answer every question", () => {
    cy.visit("/");
    cy.get("#WhistleblowingButton").click();
    cy.get("#step-0").should("be.visible");

    // the validated inputs refuse what does not fit, and say why
    cy.get("#step-0-field-0-0-input-0").type("not an address");
    cy.contains(t("please enter a valid email address.")).should("be.visible");
    cy.get("#step-0-field-0-0-input-0").clear().type("someone@example.org");
    cy.contains(t("please enter a valid email address.")).should("not.exist");

    cy.get("#step-0-field-1-0-input-0").type("twelve");
    cy.contains(t("please enter numbers only.")).should("be.visible");
    cy.get("#step-0-field-1-0-input-0").clear().type("12345");

    cy.get("#step-0-field-2-0-input-0").type("A long answer, on several lines.");

    cy.get("#step-0-field-3-0-input-0-option-0").check();
    cy.get("#step-0-field-3-0-input-0-option-1").check();
    cy.get("#step-0-field-4-0-input-0-option-1").check();
    // the first entry of the list is the empty choice: the one after it is chosen
    cy.get("#step-0-field-5-0-input-0").select(1);

    pickADay(cy.get("#step-0-field-6-0-input-0").siblings("span"), "first");
    cy.get("#step-0-field-6-0-input-0").should("not.have.value", "");

    // the two bounds of the period share the id of the question: first the start, then the end
    pickADay(cy.get("input#step-0-field-7-0-input-0").eq(0).siblings("span"), "first");
    pickADay(cy.get("input#step-0-field-7-0-input-0").eq(1).siblings("span"), "last");
    cy.get("input#step-0-field-7-0-input-0").eq(1).should("not.have.value", "");

    cy.contains("Please read the terms.").should("be.visible");
    cy.get("#step-0-field-8-0-input-0").check();

    cy.get("#step-0-field-9-0-input-0-field-0-0-input-0").type("inside the group");

    cy.takeScreenshot("whistleblower/submission_every_question");
    cy.takeScreenshot("whistleblower/submission_every_question_detail", "#step-0");

    cy.get("#SubmitButton").click();
    cy.get("#ReceiptCode").should("be.visible");
  });

  it("should show the recipient every answer", () => {
    cy.login_receiver();
    cy.visit("/#/recipient/reports");
    cy.waitForUrl("/recipient/reports");
    cy.get("#tip-0").click();
    cy.get("#TipInfoBox").should("be.visible");

    cy.get("#ReportAnswers").within(() => {
      cy.contains("someone@example.org");
      cy.contains("12345");
      cy.contains("A long answer, on several lines.");
      cy.contains("Choice A");
      cy.contains("Choice B");
      cy.contains("Choice D");
      cy.contains("Choice E");
      // the terms accepted are shown as a ticked box
      cy.get(".fa-square-check").should("exist");
      cy.contains("inside the group");
    });

    cy.takeScreenshot("recipient/report_every_question");
    cy.takeScreenshot("recipient/report_every_question_detail", "#ReportAnswers");
    cy.logout();
  });

  it("should give the channel its questionnaire back", () => {
    cy.login_admin();
    putQuestionnaireOnTheChannel("GLOBALEAKS");
    cy.logout();
  });
});
