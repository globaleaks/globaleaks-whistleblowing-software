import * as pages from '../support/pages';

describe("globaleaks process", function () {
  const N = 1;
  let receipts: any = [];
  const comment = "comment";

  const perform_submission = async (res?:string) => {
    const wbPage = pages.WhistleblowerPage;

    wbPage.performSubmission(res).then((receipt) => {
      receipts.unshift(receipt);
    });
  };

  for (let i = 1; i <= N; i++) {
    it("Whistleblowers should be able to perform a submission with single attachement", function () {
      perform_submission("single_file_upload");
    });

    it("Whistleblower actions with single attachement", function () {
      cy.login_whistleblower(receipts[0]);
      cy.logout();
    });

    it("Whistleblowers should be able to perform a submission with multiple attachement", function () {
      perform_submission();
    });

    it("Recipient actions ", function () {
      cy.login_receiver();
      cy.waitForUrl("/#/recipient/home");
      cy.visit("/#/recipient/reports");

      cy.get("#tip-0").should('be.visible').first().click();

      cy.get(".TipInfoID").invoke("text").then((_) => {
        cy.contains("summary").should("exist");

        cy.get("[name='tip.label']").type("Important");
        cy.get("#assignLabelButton").click();

        cy.get("#tip-action-star").click();
      });

      cy.waitForTipImageUpload();
      cy.get('#fileListBody').find('tr').should('have.length', 2);

      const comment = "comment";
      cy.get("[name='newCommentContent']").type(comment);
      cy.get("#comment-action-send").click();
      cy.waitForLoader();
      cy.get('#comment-0').should('contain', comment);
      cy.visit("/#/recipient/reports");
      cy.takeScreenshot("recipient/reports");

      cy.logout();
    });

    it("Whistleblower actions with multiple attachement", function () {
      const comment_reply = "comment reply";

      cy.login_whistleblower(receipts[0]);

      cy.get("#comment-0").should("contain", comment);

      cy.get("[name='newCommentContent']").type(comment_reply);
      cy.get("#comment-action-send").click();

      cy.get("#comment-0 .preformatted").should("contain", comment_reply);

      cy.takeScreenshot("whistleblower/report");

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

        cy.get("#files-action-confirm").click();
        cy.get('[data-cy="progress-bar-complete"]').should("be.visible");
      });

      cy.logout();
    });

    it("Recipient actions", function () {
      cy.login_receiver();
      cy.visit("/#/recipient/reports");

      cy.get("#tip-0").first().click();
      cy.get('#tip-action-export').invoke('click');
      cy.get(".TipInfoID").first().invoke("text").then(t => {
        expect(t.trim()).to.be.a("string");
      });
      cy.waitForLoader();
      cy.get('[id="tip-action-silence"]').should('be.visible').click();
      cy.get('#tip-action-notify').should('be.visible').click();
      cy.get('#tip-action-silence').should('be.visible').should('be.visible');
      cy.takeScreenshot("recipient/report");

      cy.logout();
    });
  }

  it("should view the whistleblower file", () => {
    cy.login_receiver();
    cy.visit("/#/recipient/reports");
    cy.get("#tip-0").first().click();
    cy.get(".tip-action-views-file").first().click();
    cy.get("#modal-action-cancel").click();
    cy.logout();
  });

  it("should not view the whistleblower file", () => {
    cy.login_receiver("Recipient2", Cypress.env("init_password") );
    cy.visit("/#/recipient/reports");
    cy.get("#tip-0").first().click();
    cy.get(".tip-action-views-file").should("be.disabled");
    cy.logout();
  });

  it("should update default channel", () => {
    cy.login_admin();
    cy.visit("/#/admin/channels");
    cy.get("#edit_context").first().click();
    cy.get('select[name="contextResolver.questionnaire_id"]').select('questionnaire 1');
    cy.get("#advance_context").click();
    cy.get('select[name="contextResolver.additional_questionnaire_id"]').select('questionnaire 2');
    cy.get("#save_context").click();
    cy.logout();
  });

  it("should run audio questionnaire and fill additional questionnaire", () => {
    cy.visit("/#/");
    cy.get("#WhistleblowingButton").click();
    cy.get("#step-0").should("be.visible");
    cy.get("#step-0-field-0-0-input-0")
    cy.get("#start_recording").click();
    cy.wait(6000);
    cy.get("#stop_recording").click();
    cy.get("#delete_recording").click();
    cy.get("#start_recording").click();
    cy.wait(6000);
    cy.get("#stop_recording").click();
    cy.get("#NextStepButton").click();
    cy.get("input[type='text']").eq(1).should("be.visible").type("abc");
    cy.get("input[type='text']").eq(2).should("be.visible").type("xyz");
    cy.get("select").first().select(1);
    cy.get("#SubmitButton").should("be.visible");
    cy.get("#SubmitButton").click();
    cy.get('.mt-md-3.clearfix.ng-star-inserted').find('#ReceiptButton').click();
    cy.get("#open_additional_questionnaire").click();
    cy.get("input[type='text']").eq(1).should("be.visible").type("single line text input");
    cy.get("#SubmitButton").click();
    cy.logout();
  });

  it("should request for identity", () => {
    cy.login_receiver();
    cy.visit("/#/recipient/reports");
    cy.get("#tip-0").first().click();
    cy.get('[data-cy="identity_toggle"]').click();
    cy.get("#identity_access_request").click();
    cy.get('textarea[name="request_motivation"]').type("This is the motivation text.");
    cy.get('#modal-action-ok').click();
    cy.logout();
  });

  it("should deny authorize identity", () => {
    cy.login_custodian();
    cy.get("#custodian_requests").first().click();
    cy.get("#deny").first().click();
    cy.get('#motivation').type("This is the motivation text.");
    cy.get('#modal-action-ok').click();
    cy.logout();
  });

  it("should request for identity", () => {
    cy.login_receiver();
    cy.visit("/#/recipient/reports");
    cy.get("#tip-0").first().click();
    cy.get('[data-cy="identity_toggle"]').click();
    cy.get("#identity_access_request").click();
    cy.get('textarea[name="request_motivation"]').type("This is the motivation text.");
    cy.get('#modal-action-ok').click();
    cy.logout();
  });

  it("should authorize identity", () => {
    cy.login_custodian();
    cy.get("#custodian_requests").first().click();
    cy.get("#authorize").first().click();
    cy.logout();
  });

  it("should revert default channel", () => {
    cy.login_admin();
    cy.visit("/#/admin/channels");
    cy.get("#edit_context").first().click();
    cy.get('select[name="contextResolver.questionnaire_id"]').select('GLOBALEAKS');
    cy.get("#save_context").click();
    cy.logout();
  });

  it("should mask reported data", function () {
    cy.login_receiver();
    cy.visit("/#/recipient/reports");
    cy.get("#tip-0").first().click();
    cy.get('[id="tip-action-mask"]').should('be.visible').click();
    cy.get("#edit-question").should('be.visible').first().click();

    cy.get('textarea[name="controlElement"]').should('be.visible').then((textarea: any) => {
      const val = textarea.val();
      cy.get('textarea[name="controlElement"]').should('be.visible').clear().type(val);
      cy.get("#select_content").click();
      cy.wait(1000);
    });
    cy.get("#save_masking").click();
    cy.get('[id="tip-action-mask"]').should('be.visible').click();
    cy.get("#edit-question").should('be.visible').first().click();
    cy.get('textarea[name="controlElement"]').should('be.visible').then((textarea: any) => {
      const val = textarea.val();
      cy.get('textarea[name="controlElement"]').should('be.visible').clear().type(val);
      cy.get("#unselect_content").click();
      cy.wait(1000);
    });
    cy.get("#save_masking").click();
    cy.logout();
  });
});
