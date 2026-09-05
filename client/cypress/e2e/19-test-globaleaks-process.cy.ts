import {t} from "../support/i18n";
import * as pages from '../support/pages';

// The list holds the reports of the reporting people and the ones the exchanges create
const openOrdinaryReport = () => {
  cy.visit("/#/recipient/reports");
  cy.waitForUrl("/recipient/reports");
  // the heading row carries the channel filter with the channel names: match on the rows, not on the
  // text alone
  cy.contains("#TipList tr.tip-action-open", "Default").first().click();
  cy.get("#TipInfoBox").should("be.visible");
};

// A panel renders its body only when open: captured closed it is an empty strip
const expandPanel = (selector: string) => {
  cy.get(selector).should("be.visible").then(($panel) => {
    // the body exists only while the panel is open: that decides whether the header has to be
    // clicked
    if ($panel.find(".card-body").length === 0) {
      cy.get(`${selector} .card-header`).click();
    }
  });
};

describe("globaleaks process", function () {
  const receipts: any = [];

  const perform_submission = (n: number) => {
    return pages.WhistleblowerPage.performSubmission(n).then((receipt) => {
      receipts.unshift(receipt);
      return receipt;
    });
  };

  it("Whistleblower should be able to file a report with 0 attachments", function () {
    return perform_submission(0);
  });

  it("Whistleblower should be able to file a report with 1 attachments", function () {
    return perform_submission(1);
  });

  it("Whistleblower should be able to file a report with 2 attachments", function () {
    return perform_submission(2);
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
        input[0]!.dispatchEvent(changeEvent);
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
    cy.get("#tip-0").first().click();

    cy.get("#TipInfoBox").should("be.visible");
    cy.takeScreenshot("recipient/report");

    cy.takeScreenshot("recipient/report_label", "#TipLabelBox");
    cy.takeScreenshot("recipient/report_info", "#TipInfoBox");
    cy.takeScreenshot("recipient/report_files", "#TipPageFilesInfoBox");
    cy.takeScreenshot("recipient/report_comments", "#TipCommentsBox");
    cy.takeScreenshot("recipient/report_uploads", "#TipUploadBox");

    cy.get(".TipInfoID").invoke("text").then(() => {
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
    cy.get('#actionsDropdownButton').click();
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
    const formattedDate = tomorrow.toISOString().split('T')[0] ?? "";
    cy.get('input[name="dp"]').click().clear();
    cy.get('input[name="dp"]').click().type(formattedDate);
    cy.get('#modal-action-ok').click();

    // Silence email notifications
    cy.get('[id="tip-action-silence"]').click();
    cy.get('#tip-action-notify').click();
    cy.get('#tip-action-silence').should('be.visible').should('be.visible');

    // Upload file
    cy.get('#upload_description')
      .type('description')
      .should('have.value', 'description');

    cy.get('input[type="file"]').selectFile(
      './cypress/fixtures/files/test.txt',
      { force: true }
    );

    cy.get('.download-button').should('be.visible');
    cy.get('.download-button').first().click();

    // View files uploaded by the whistleblower
    cy.get(".tip-action-views-file").first().click();
    cy.get("#modal-action-cancel").click();

    // Mask information
    cy.get('#actionsDropdownButton').click();
    cy.takeScreenshot("recipient/menu_actions_option_mask", "#tip-action-mask");
    cy.get('[id="tip-action-mask"]').click();

    cy.takeScreenshot("recipient/report_with_masking_enabled_questionnaire_detail", "#ReportAnswers");
    cy.takeScreenshot("recipient/report_with_masking_enabled_files_detail", "#ReportAttachments");

    cy.get("#edit-question").first().click();
    cy.takeScreenshot("recipient/modal_mask_1", ".modal-dialog");
    cy.get('textarea[name="controlElement"]').should('be.visible').then((textarea: any) => {
      const val = textarea.val();
      cy.get('textarea[name="controlElement"]').should('be.visible').clear().type(val);
      cy.get("#select_content").click();
      cy.takeScreenshot("recipient/modal_mask_2", ".modal-dialog");
    });
    cy.get("#save_masking").click();

    cy.get('#actionsDropdownButton').click();
    cy.get('[id="tip-action-mask"]').click();
    cy.takeScreenshot("recipient/report_after_masking", "#ReportAnswers");

    cy.get('#actionsDropdownButton').click();
    cy.get('[id="tip-action-mask"]').click();
    cy.get("#edit-question").first().click();
    cy.get('textarea[name="controlElement"]').should('be.visible').then((textarea: any) => {
      const val = textarea.val();
      cy.get('textarea[name="controlElement"]').should('be.visible').clear().type(val);
      cy.get("#unselect_content").click();
    });
    cy.get("#save_masking").click();

    cy.get('#actionsDropdownButton').click();
    cy.get('[id="tip-action-mask"]').click();

    // Download
    cy.get('#exportDropdownButton').click();
    cy.takeScreenshot("recipient/menu_export", ".dropdown-menu.show");
    cy.takeScreenshot("recipient/menu_export_option_download", "#tip-action-export");
    cy.takeScreenshot("recipient/menu_export_option_print", "#tip-action-print");
    cy.get('#tip-action-export').invoke('click');
    cy.get(".TipInfoID").first().invoke("text").then(t => {
      expect(t.trim()).to.be.a("string");
    });

    // Close and reopen
    cy.get('#actionsDropdownButton').click();
    cy.takeScreenshot("recipient/menu_actions_option_change_status", "#tip-action-change-status");
    cy.get("#tip-action-change-status").click();
    cy.takeScreenshot("recipient/modal_change_status", ".modal-dialog");
    cy.get('#assignSubmissionStatus').select(2);
    cy.get("#modal-action-ok").click();
    cy.get('#actionsDropdownButton').click();
    cy.get("#tip-action-reopen").click();
    cy.get("#modal-action-ok").click();

    // Grant access to Recipient3
    cy.get('#usersDropdownButton').click();
    cy.takeScreenshot("recipient/menu_users", ".dropdown-menu.show");
    cy.takeScreenshot("recipient/menu_users_option_grant_access", "#tip-action-grant-access");
    cy.get("#tip-action-grant-access").click();
    cy.takeScreenshot("recipient/modal_grant_access", ".modal-dialog");
    cy.get('[data-cy="receiver_selection"]').click();
    cy.get('.ng-dropdown-panel').should('be.visible');
    cy.get('[data-cy="receiver_selection"]').click();
    cy.contains('.ng-option', 'Recipient3').click();
    cy.get("#modal-action-ok").click();

    // The operation keeps the page busy for a moment and a navigation issued meanwhile is undone by
    // the router: wait for the modal to be gone
    cy.get(".modal-dialog").should("not.exist");
    cy.waitForPageIdle();

    // Navigate list and acquire screenshot for documentation
    cy.visit("/#/recipient/reports");
    cy.waitForUrl("/#/recipient/reports");
    cy.takeScreenshot("recipient/reports");

    cy.get("#tip-0").first().click();

    // Revoke access to Recipient2
    cy.get('#usersDropdownButton').click();
    cy.takeScreenshot("recipient/menu_users", ".dropdown-menu.show");
    cy.takeScreenshot("recipient/menu_users_option_revoke_access", "#tip-action-revoke-access");
    cy.get("#tip-action-revoke-access").click();
    cy.takeScreenshot("recipient/modal_revoke_access", ".modal-dialog");
    cy.get('[data-cy="receiver_selection"]').click();
    cy.get('.ng-dropdown-panel').should('be.visible');
    cy.get('[data-cy="receiver_selection"]').click();
    cy.contains('.ng-option', 'Recipient2').click();
    cy.get("#modal-action-ok").click();

    // Delete report
    cy.get('#actionsDropdownButton').click();
    cy.takeScreenshot("recipient/menu_actions_option_delete_report", "#tip-action-delete-report");
    cy.get("#tip-action-delete-report").click();
    cy.takeScreenshot("recipient/modal_delete_report", ".modal-dialog");
    cy.get("#modal-action-ok").click();

    cy.get(".modal-dialog").should("not.exist");
    cy.waitForUrl("/#/recipient/reports");

    cy.get("#tip-0").first().click();

    // Transfer access to Recipient3
    cy.get('#usersDropdownButton').click();
    cy.takeScreenshot("recipient/menu_users_option_transfer_access", "#tip-action-transfer-access");
    cy.get("#tip-action-transfer-access").click();
    cy.takeScreenshot("recipient/modal_transfer_access", ".modal-dialog");
    cy.get('[data-cy="receiver_selection"]').click();
    cy.get('.ng-dropdown-panel').should('be.visible');
    cy.get('[data-cy="receiver_selection"]').click();
    cy.contains('.ng-option', 'Recipient3').click();
    cy.get("#modal-action-ok").click();

    cy.get(".modal-dialog").should("not.exist");
    cy.waitForUrl("/#/recipient/reports");
  });

  it("Recipient should be able to work the list of the reports", function () {
    cy.login_receiver();
    cy.visit("/#/recipient/reports");

    cy.get('#search-filter-input').type("your search term");
    cy.get('#search-filter-input').clear();
    cy.get('th.TipInfoID').click();
    cy.get('#filter-context_name').click();
    cy.get('.multiselect-item-checkbox').eq(1).click();
    cy.get('.multiselect-item-checkbox').eq(0).click();
    cy.get('#filter-creation_date').click();
    cy.get('.custom-date-selector').first().click();
    cy.get('.custom-date-selector').eq(4).click({ shiftKey: true });
    cy.contains('button.btn.btn-danger', 'Reset').click();

    cy.get('#tip-action-select-all').click();
    cy.visit("/#/recipient/reports");
    cy.get('#tip-action-export').click();

    cy.get("#tip-action-enter-report").click();
    cy.get(".modal-dialog").should("be.visible");
    cy.takeScreenshot("recipient/insert_report");
    cy.takeScreenshot("recipient/insert_report_detail", ".modal-dialog");
    cy.get("#InsertionForm").should("be.visible");
    cy.get(".modal-header .btn-close").click();

    cy.logout();
  });

  it("should update default channel", () => {
    cy.login_admin();
    cy.visit("/#/admin/channels");
    cy.get("[data-action='edit']").first().click();
    cy.get('select[name="contextResolver.questionnaire_id"]').should("be.visible").select('questionnaire 1');
    cy.get("#advance_context").click();
    // The channel names the additional questionnaires and elects one as automatic; the other is left
    // to the recipients
    cy.get(".add-additional-questionnaire-btn").click();
    cy.get("#AdditionalQuestionnaireAdder ng-select").click();
    cy.get("div.ng-option").contains("questionnaire 2").click();
    cy.get("ul.selection-list li").should("contain", "questionnaire 2");
    cy.get("ul.selection-list li .non-default-entry").click();
    cy.get("ul.selection-list li .clear-default-btn").should("be.visible");
    cy.get(".add-additional-questionnaire-btn").click();
    cy.get("#AdditionalQuestionnaireAdder ng-select").click();
    cy.get("div.ng-option").contains("duplicate questionnaire").click();
    cy.get("ul.selection-list li").should("contain", "duplicate questionnaire");
    cy.get("[data-action='save']").click();
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
    cy.get("#delete_recording").click();
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
    // Answered: nothing more is asked until the recipients ask again
    cy.get("#open_additional_questionnaire").should("not.exist");
    cy.logout();
  });

  it("should ask a further questionnaire of the report and withdraw it", () => {
    cy.login_receiver();
    cy.visit("/#/recipient/reports");
    cy.get("#tip-0").first().click();

    cy.get("#actionsDropdownButton").click();
    cy.get("#tip-action-request-additional-questionnaire").should("be.visible").click();
    cy.get('[data-cy="questionnaire_selection"]').click();
    cy.get(".ng-option").contains("duplicate questionnaire").click();
    cy.get("#modal-action-ok").click();

    // The request stands and is shown to the recipients that asked it, chosen where it is decided
    // again
    cy.get("#edit_additional_questionnaire").should("be.visible");
    cy.get("#actionsDropdownButton").click();
    cy.get("#tip-action-request-additional-questionnaire").click();
    cy.get('[data-cy="questionnaire_selection"]').contains("duplicate questionnaire");
    cy.get("#modal-action-cancel").click();

    // Edited from the report itself: leaving nothing chosen withdraws it
    cy.get("#edit_additional_questionnaire").click();
    cy.get('[data-cy="questionnaire_selection"]').contains("duplicate questionnaire");
    cy.get('[data-cy="questionnaire_selection"] .ng-clear-wrapper').click();
    cy.get("#modal-action-ok").click();
    cy.get("#edit_additional_questionnaire").should("not.exist");

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
    cy.waitForUrl("/#/recipient/reports");
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
    cy.waitForUrl("/#/recipient/reports");
    cy.get("#tip-0").first().click();
    cy.takeScreenshot("recipient/identity_post_authorization", "#Identity");
    cy.logout();
  });

  // the audit log of a report lists the operations performed on it.
  it("should access report audit log", () => {
    cy.login_receiver();
    cy.visit("/#/recipient/reports");
    cy.get("#tip-0").first().click();
    cy.get("#tip-action-access-audit-log").click();
    cy.takeScreenshot("recipient/report_audit_log", ".modal-dialog");
    cy.get("#modal-action-cancel").click();
    cy.logout();
  });

  it("should revert default channel", () => {
    cy.login_admin();
    cy.visit("/#/admin/channels");
    cy.get("[data-action='edit']").first().click();
    cy.get('select[name="contextResolver.questionnaire_id"]').select('GLOBALEAKS');
    cy.get("[data-action='save']").click();
    cy.logout();
  });

  it("should mark the comments the other side has read", () => {
    pages.WhistleblowerPage.performSubmission(0).then((receipt) => {
      cy.login_receiver();
      openOrdinaryReport();
      expandPanel("#TipCommentsBox");
      cy.get("[name='newCommentContent']").should("be.visible").type("Answer of the recipient");
      cy.get("#comment-action-send").click();
      cy.get("#comment-0").should("contain", "Answer of the recipient");

      // a file is attached too: its receipt is the download by the other side
      expandPanel("#TipPageRFileUpload");
      cy.get("#upload_description").first().should("be.visible").type("attachment of the recipient");
      cy.get('input[type="file"]').selectFile("./cypress/fixtures/files/test.txt", {force: true});
      cy.get("#TipPageRFileUpload .download-button").should("be.visible");
      cy.logout();

      // the reporting person reads the answer and replies
      cy.login_whistleblower(String(receipt));
      cy.get("#TipInfoBox").should("be.visible");
      expandPanel("#TipCommentsBox");
      cy.get("#comment-0").should("contain", "Answer of the recipient");
      cy.get("[name='newCommentContent']").should("be.visible").type("Reply of the reporting person");
      cy.get("#comment-action-send").click();
      cy.get("#comment-0").should("contain", "Reply of the reporting person");
      // the download opens in a window of its own, out of reach of an intercept: the receipt
      // on the file is set by it, so it is given the time to complete
      cy.get(".download-button").first().click();
      cy.wait(3000);
      cy.logout();

      // the recipient is shown that its answer has been read, and its file downloaded
      cy.login_receiver();
      openOrdinaryReport();
      expandPanel("#TipCommentsBox");
      cy.get("#TipCommentsBox .text-success .fa-check").should("exist");
      cy.takeScreenshot("recipient/tip_comments_read_receipt");
      cy.takeScreenshot("recipient/tip_comments_read_receipt_detail", "#TipCommentsBox");
      expandPanel("#TipPageRFileUpload");
      cy.get("#TipPageRFileUpload .text-success .fa-check").should("exist");
      cy.takeScreenshot("recipient/tip_files_read_receipt_detail", "#TipUploadBox");

      // the list marks the reports whose last update the reporting person has read
      cy.visit("/#/recipient/reports");
      cy.waitForUrl("/#/recipient/reports");
      cy.get("#TipList").should("be.visible");
      cy.takeScreenshot("recipient/tips_read_receipt_detail", "#TipList");
      cy.logout();

      // the reporting person is shown that its reply has been read
      cy.login_whistleblower(String(receipt));
      cy.get("#TipInfoBox").should("be.visible");
      expandPanel("#TipCommentsBox");
      cy.get("#TipCommentsBox .text-success .fa-check").should("exist");
      cy.takeScreenshot("whistleblower/tip_comments_read_receipt");
      cy.takeScreenshot("whistleblower/tip_comments_read_receipt_detail", "#TipCommentsBox");
      cy.logout();
    });
  });
});

describe("report audit log", () => {
  // among them the upload of the attachments and the accesses to them.
  it("should list the operations on the report and on its files", () => {
    cy.login_receiver();
    openOrdinaryReport();

    cy.takeScreenshot("admin/report_audit_log_button_detail", "#TipToolbar");

    // A report without attachments produces no file events: one is attached and downloaded here
    expandPanel("#TipPageRFileUpload");
    cy.get("#upload_description").first().should("be.visible").type("attachment of the recipient");
    cy.get('input[type="file"]').selectFile("./cypress/fixtures/files/test.txt", {force: true});
    cy.get(".download-button").first().click();

    cy.get("#tip-action-access-audit-log").click();
    cy.get(".modal").should("be.visible");
    cy.takeScreenshot("admin/report_audit_log", ".modal-dialog");

    cy.get(`.modal input[placeholder*='${t("Search")}']`).first().should("be.visible").type("file");
    cy.contains(".modal", "file").should("be.visible");
    cy.takeScreenshot("admin/report_audit_log_files");
    cy.takeScreenshot("admin/report_audit_log_files_detail", ".modal-dialog");
    cy.get("#modal-action-cancel").click();

    cy.logout();
  });

  it("should filter the reports that are new or updated", () => {
    cy.login_receiver();
    cy.visit("/#/recipient/reports");
    cy.waitForUrl("/recipient/reports");

    cy.get("#filterOpt").should("exist").check({ force: true });
    cy.takeScreenshot("recipient/tips_unread_filter");
    cy.takeScreenshot("recipient/tips_unread_filter_detail", "#TipList");
    cy.get("#filterOpt").uncheck({ force: true });

    cy.logout();
  });

  it("should show the recipients that have access to a report", () => {
    cy.login_receiver();
    cy.visit("/#/recipient/reports");
    cy.waitForUrl("/recipient/reports");

    cy.get(".TipInfoRecipientCount").first().should("be.visible");
    cy.takeScreenshot("recipient/tips_recipients_count");
    cy.get(".TipInfoRecipientCount span").first().trigger("mouseenter");
    cy.takeScreenshot("recipient/tips_recipients_count_detail", "#TipList");

    cy.logout();
  });
});

describe("fingerprints of the deleted content", () => {
  // What is deleted leaves its fingerprints on the log, read by the recipient and by the
  // whistleblower
  // The attachments reach the recipients through the delivery job, a few seconds after the
  // submission: the report is opened again until the file is there
  const openOrdinaryReportWithItsFile = (attempt = 0) => {
    openOrdinaryReport();
    cy.get("body").then(($body) => {
      if ($body.find("#fileListBody tr").length > 0) {
        return;
      }

      expect(attempt, "attempts made waiting for the delivery").to.be.lessThan(12);
      cy.wait(5000);
      openOrdinaryReportWithItsFile(attempt + 1);
    });
  };

  it("should keep on the log the fingerprints of a deleted attachment", () => {
    pages.WhistleblowerPage.performSubmission(1).then((receipt) => {
      cy.login_receiver();
      openOrdinaryReportWithItsFile();

      // deleting an attachment lives in the masking mode: masked first, then redacted away
      cy.get("#actionsDropdownButton").click();
      cy.get("#tip-action-mask").click();

      cy.get("#ReportAttachments .fa-eraser").first().click();
      cy.get("#ReportAttachments .tip-action-delete-file").should("be.visible").first().click();

      cy.get("#tip-action-access-audit-log").click();
      cy.get(".modal").should("be.visible");
      cy.contains(".modal", "delete_file").should("be.visible");

      // the details of an entry open from the entry: two named fingerprints
      cy.contains(".modal tr", "delete_file").find('[data-action="toggle"]').click();
      cy.get('.modal [data-cy="audit-details"]').should("be.visible");
      cy.contains('.modal [data-cy="audit-details"]', "sha256:").should("be.visible");
      cy.contains('.modal [data-cy="audit-details"]', "sha512:").should("be.visible");

      cy.takeScreenshot("recipient/report_audit_log_hashes");
      cy.takeScreenshot("recipient/report_audit_log_hashes_detail", ".modal-dialog");

      cy.get("#modal-action-cancel").click();
      cy.logout();

      cy.login_whistleblower(String(receipt));
      cy.get("#TipInfoBox").should("be.visible");
      cy.get("#tip-action-access-audit-log").click();
      cy.get(".modal").should("be.visible");
      cy.contains(".modal", "delete_file").should("be.visible");

      // the details of an entry open from the entry: two named fingerprints
      cy.contains(".modal tr", "delete_file").find('[data-action="toggle"]').click();
      cy.get('.modal [data-cy="audit-details"]').should("be.visible");
      cy.contains('.modal [data-cy="audit-details"]', "sha256:").should("be.visible");
      cy.contains('.modal [data-cy="audit-details"]', "sha512:").should("be.visible");

      cy.takeScreenshot("whistleblower/report_audit_log_hashes");
      cy.takeScreenshot("whistleblower/report_audit_log_hashes_detail", ".modal-dialog");

      cy.get("#modal-action-cancel").click();
      cy.logout();
    });
  });
});
