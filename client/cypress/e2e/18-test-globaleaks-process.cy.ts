import * as pages from '../support/pages';

describe("globaleaks process", function () {
  let receipts: any = [];

  const perform_submission = async (number_of_attachments:number) => {
    const wbPage = pages.WhistleblowerPage;

    wbPage.performSubmission(number_of_attachments).then((receipt) => {
      receipts.unshift(receipt);
    });
  };

  it("Whistleblower should be able to file a report with 0 attachments", function () {
    perform_submission(0);
  });

  it("Whistleblower should be able to file a report with 1 attachments", function () {
    perform_submission(1);
  });

  it("Whistleblower should be able to file a report with 2 attachments", function () {
    perform_submission(2);
  });

  it("Whistleblower should be able to access a report with the receipt and perform further actions", function () {
    const comment_reply = "comment reply";

    cy.login_whistleblower(receipts[0]);

    cy.get("#TipInfoBox").should("be.visible");
    cy.takeScreenshot("whistleblower/report");
    cy.takeScreenshot("whistleblower/report_info", "#TipInfoBox");
    cy.takeScreenshot("whistleblower/report_files", "#TipPageFilesInfoBox");
    cy.takeScreenshot("whistleblower/report_comments", "#TipCommentsBox");

    cy.get("[name='newCommentContent']").type(comment_reply);
    cy.get("#comment-action-send").click();

    cy.get("#comment-0 .preformatted").should("contain", comment_reply);

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

  it("Recipient should be able to access a report and perform further actions", function () {
    cy.login_receiver();

    cy.visit("/#/recipient/reports");
    cy.waitForUrl("/#/recipient/reports");
    cy.get("#tip-0").should('be.visible').first().click();

    cy.get("#TipInfoBox").should("be.visible");
    cy.takeScreenshot("recipient/report");

    cy.takeScreenshot("recipient/report_label", "#TipLabelBox");
    cy.takeScreenshot("recipient/report_info", "#TipInfoBox");
    cy.takeScreenshot("recipient/report_files", "#TipPageFilesInfoBox");
    cy.takeScreenshot("recipient/report_comments", "#TipCommentsBox");
    cy.takeScreenshot("recipient/report_uploads", "#TipUploadBox");

    cy.get(".TipInfoID").invoke("text").then((_) => {
      cy.contains("summary").should("exist");

      cy.get("[name='tip.label']").type("Important");
      cy.get("#assignLabelButton").click();

      cy.get("#tip-action-star").click();
    });

    const comment = "comment";
    cy.get("[name='newCommentContent']").type(comment);
    cy.get("#comment-action-send").click();
    cy.get('#comment-0').should('contain', comment);

    // Change the expiration date
    cy.get('#actionsDropdown').click();
    cy.takeScreenshot("recipient/menu_actions", ".dropdown-menu.show");
    cy.takeScreenshot("recipient/menu_actions_option_postpone", "#tip-action-postpone");
    cy.get("#tip-action-postpone").click();
    cy.takeScreenshot("recipient/modal_postpone", ".modal-dialog");
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

    // Set a reminder
    cy.get("#tip-action-reminder").click();
    cy.takeScreenshot("recipient/modal_reminder", ".modal-dialog");
    cy.get('.modal').should('be.visible');
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    const formattedDate = tomorrow.toISOString().split('T')[0];
    cy.get('input[name="dp"]').click().clear();
    cy.get('input[name="dp"]').click().type(formattedDate);
    cy.get('#modal-action-ok').click();

    // Silence email notifications
    cy.get('[id="tip-action-silence"]').should('be.visible').click();
    cy.get('#tip-action-notify').should('be.visible').click();
    cy.get('#tip-action-silence').should('be.visible').should('be.visible');

    // Upload and delete file
    cy.get('#upload_description')
      .type('description')
      .should('have.value', 'description');

    cy.get('input[type="file"]').selectFile(
      './cypress/fixtures/files/test.txt',
      { force: true }
    );

    cy.get('.download-button').should('be.visible');
    cy.get('.download-button').first().click();
    cy.get('.tip-action-delete-file').first().click();

    // View files uploaded by the whistleblower
    cy.get(".tip-action-views-file").first().click();
    cy.get("#modal-action-cancel").click();

    // Mask information
    cy.get('#actionsDropdown').click();
    cy.takeScreenshot("recipient/menu_actions_option_mask", "#tip-action-mask");
    cy.get('[id="tip-action-mask"]').should('be.visible').click();

    cy.takeScreenshot("recipient/report_with_masking_enabled_questionnaire_detail", "#ReportAnswers");
    cy.takeScreenshot("recipient/report_with_masking_enabled_files_detail", "#ReportAttachments");

    cy.get("#edit-question").should('be.visible').first().click();
    cy.takeScreenshot("recipient/modal_mask_1", ".modal-dialog");
    cy.get('textarea[name="controlElement"]').should('be.visible').then((textarea: any) => {
      const val = textarea.val();
      cy.get('textarea[name="controlElement"]').should('be.visible').clear().type(val);
      cy.get("#select_content").click();
      cy.takeScreenshot("recipient/modal_mask_2", ".modal-dialog");
    });
    cy.get("#save_masking").click();

    cy.get('#actionsDropdown').click();
    cy.get('[id="tip-action-mask"]').should('be.visible').click();
    cy.takeScreenshot("recipient/report_after_masking", "#ReportAnswers");

    cy.get('#actionsDropdown').click();
    cy.get('[id="tip-action-mask"]').should('be.visible').click();
    cy.get("#edit-question").should('be.visible').first().click();
    cy.get('textarea[name="controlElement"]').should('be.visible').then((textarea: any) => {
      const val = textarea.val();
      cy.get('textarea[name="controlElement"]').should('be.visible').clear().type(val);
      cy.get("#unselect_content").click();
    });
    cy.get("#save_masking").click();

    cy.get('#actionsDropdown').click();
    cy.get('[id="tip-action-mask"]').should('be.visible').click();

    // Download
    cy.get('#exportDropdown').click();
    cy.takeScreenshot("recipient/menu_export", ".dropdown-menu.show");
    cy.takeScreenshot("recipient/menu_export_option_download", "#tip-action-export");
    cy.takeScreenshot("recipient/menu_export_option_print", "#tip-action-print");
    cy.get('#tip-action-export').invoke('click');
    cy.get(".TipInfoID").first().invoke("text").then(t => {
      expect(t.trim()).to.be.a("string");
    });

    // Close and reopen
    cy.get('#actionsDropdown').click();
    cy.takeScreenshot("recipient/menu_actions_option_change_status", "#tip-action-change-status");
    cy.get("#tip-action-change-status").click();
    cy.takeScreenshot("recipient/modal_change_status", ".modal-dialog");
    cy.get('#assignSubmissionStatus').select(2);
    cy.get("#modal-action-ok").click();
    cy.get('#actionsDropdown').click();
    cy.get("#tip-action-reopen").click();
    cy.get("#modal-action-ok").click();

    // Grant access to Recipient3
    cy.get('#usersDropdown').click();
    cy.takeScreenshot("recipient/menu_users_option_grant_access", "#tip-action-grant-access");
    cy.get("#tip-action-grant-access").should('be.visible').click();
    cy.takeScreenshot("recipient/modal_grant_access", ".modal-dialog");
    cy.get('[data-cy="receiver_selection"]').click();
    cy.get('.ng-dropdown-panel').should('be.visible');
    cy.get('[data-cy="receiver_selection"]').click();
    cy.contains('.ng-option', 'Recipient3').click();
    cy.get("#modal-action-ok").click();

    // Navigate list and acquire screenshot for documentation
    cy.visit("/#/recipient/reports");
    cy.waitForUrl("/#/recipient/reports");
    cy.takeScreenshot("recipient/reports");

    cy.get("#tip-0").first().click();

    // Revoke access to Recipient2
    cy.get('#usersDropdown').click();
    cy.takeScreenshot("recipient/menu_users", ".dropdown-menu.show");
    cy.takeScreenshot("recipient/menu_users_option_revoke_access", "#tip-action-revoke-access");
    cy.get("#tip-action-revoke-access").should('be.visible').click();
    cy.takeScreenshot("recipient/modal_revoke_access", ".modal-dialog");
    cy.get('[data-cy="receiver_selection"]').click();
    cy.get('.ng-dropdown-panel').should('be.visible');
    cy.get('[data-cy="receiver_selection"]').click();
    cy.contains('.ng-option', 'Recipient2').click();
    cy.get("#modal-action-ok").click();

    // Delete report
    cy.get('#actionsDropdown').click();
    cy.takeScreenshot("recipient/menu_actions_option_delete_report", "#tip-action-delete-report");
    cy.get("#tip-action-delete-report").should('be.visible').click();
    cy.takeScreenshot("recipient/modal_delete_report", ".modal-dialog");
    cy.get("#modal-action-ok").click();

    cy.waitForUrl("/#/recipient/reports");

    cy.get("#tip-0").first().click();

    // Transfer access to Recipient3
    cy.get('#usersDropdown').click();
    cy.takeScreenshot("recipient/menu_users_option_transfer_access", "#tip-action-transfer-access");
    cy.get("#tip-action-transfer-access").should('be.visible').click();
    cy.takeScreenshot("recipient/modal_transfer_access", ".modal-dialog");
    cy.get('[data-cy="receiver_selection"]').click();
    cy.get('.ng-dropdown-panel').should('be.visible');
    cy.get('[data-cy="receiver_selection"]').click();
    cy.contains('.ng-option', 'Recipient3').click();
    cy.get("#modal-action-ok").click();

    cy.waitForUrl("/#/recipient/reports");
  });

  it("should update default channel", () => {
    cy.login_admin();
    cy.visit("/#/admin/channels");
    cy.get("#edit_context").first().click();
    cy.get('select[name="contextResolver.questionnaire_id"]').should("be.visible").select('questionnaire 1');
    cy.get("#advance_context").click();
    cy.get('select[name="contextResolver.additional_questionnaire_id"]').should("be.visible").select('questionnaire 2');
    cy.get("#save_context").click();
    cy.logout();
  });

  it("should run audio questionnaire, provide identity and fill additional questionnaire", () => {
    cy.visit("/#/");
    cy.get("#WhistleblowingButton").click();
    cy.get("#step-0").should("be.visible");
    cy.get("#step-0-field-0-0-input-0")
    cy.get("#start_recording").click();
    cy.wait(10000);
    cy.get("#stop_recording").click();
    cy.get("#delete_recording").should("be.visible").click();
    cy.get("#start_recording").click();
    cy.wait(10000);
    cy.get("#stop_recording").click();
    cy.get("#delete_recording").should("be.visible");
    cy.get("#NextStepButton").click();
    cy.takeScreenshot("whistleblower/report_identity", "#SubmissionTabsContentBox");
    cy.get("input[type='text']").eq(2).should("be.visible").type("abc");
    cy.get("input[type='text']").eq(3).should("be.visible").type("xyz");
    cy.get("select").first().select(1);
    cy.get("#SubmitButton").should("be.visible");
    cy.get("#SubmitButton").click();
    cy.get("#ViewReportButton").should("be.visible");
    cy.wait(5000);
    cy.get("#ViewReportButton").click();
    cy.get("#open_additional_questionnaire").click();
    cy.get("input[type='text']").eq(1).should("be.visible").type("single line text input");
    cy.get("#SubmitButton").click();
    cy.logout();
  });

  it("should request for identity", () => {
    cy.login_receiver();
    cy.visit("/#/recipient/reports");
    cy.get("#tip-0").first().click();
    cy.takeScreenshot("recipient/identity_pre_authorization", "#Identity");
    cy.get("#identity_access_request").click();
    cy.takeScreenshot("recipient/modal_identity_request", ".modal-dialog");
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

  it("should request for identity (second time)", () => {
    cy.login_receiver();
    cy.visit("/#/recipient/reports");
    cy.get("#tip-0").first().click();
    cy.takeScreenshot("recipient/identity_post_denial", "#Identity");
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

  it("should request for identity (second time)", () => {
    cy.login_receiver();
    cy.visit("/#/recipient/reports");
    cy.get("#tip-0").first().click();
    cy.takeScreenshot("recipient/identity_post_authorization", "#Identity");
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
});
