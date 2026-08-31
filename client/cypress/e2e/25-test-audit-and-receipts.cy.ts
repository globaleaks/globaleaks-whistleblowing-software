import * as pages from '../support/pages';

// The audit log lives in two places: it stays a section of the administrative
// interface, now behind the can_manage_auditlog permission, and it is the only
// section of the area of the auditor, the role introduced for the oversight of
// the platform.
describe("auditor audit log", () => {
  // The auditor reaches the audit log with its own credentials and reads there
  // the operations performed on the platform; the administrative sections are
  // not offered to it.
  it("should reach the audit log with the credentials of the auditor", () => {
    cy.login_auditor();

    cy.waitForUrl("/auditor/home");
    cy.get("#auditor_audit_log").click();
    cy.waitForUrl("/auditor/auditlog");

    cy.get("src-auditlog-tab1 tbody tr").should("have.length.greaterThan", 0);

    // the area is photographed once, by the spec that acquires the images:
    // repeating the login and the navigation here bought two captures at the
    // price of a whole session

    cy.logout();
  });

});

describe("administrator audit log", () => {
  // TC.38: the administrator restricts the audit log to a range of dates.
  it("should filter the audit log by date", () => {
    cy.login_admin();
    cy.visit("/#/admin/auditlog");
    cy.get("#filter-date").click();

    // the day cells are rendered by a custom template of the range picker
    cy.get(".custom-date-selector").should("have.length.greaterThan", 1);
    cy.get(".custom-date-selector").first().click();
    cy.get(".custom-date-selector").last().click();

    cy.get("#filter-date").should("have.class", "filter-active");
    cy.takeScreenshot("admin/audit_log_date_filter_detail", "src-auditlog-tab1 thead");

    cy.logout();
  });

  // TC.39: the administrator restricts the audit log to a single user.
  it("should filter the audit log by user", () => {
    cy.login_admin();
    cy.visit("/#/admin/auditlog");
    cy.get("#filter-username").click();

    // a capture changes the viewport and the list of the users closes with it:
    // the user is chosen first, and the captures are taken afterwards
    cy.get("ng-multiselect-dropdown .multiselect-item-checkbox").should("be.visible");
    cy.get("ng-multiselect-dropdown .multiselect-item-checkbox").first().click();

    cy.get("#filter-username").should("have.class", "filter-active");
    cy.takeScreenshot("admin/audit_log_user_filtered");

    cy.get("#filter-username").click();
    cy.get("ng-multiselect-dropdown .multiselect-item-checkbox").should("be.visible");
    cy.takeScreenshot("admin/audit_log_user_filter_detail", "src-auditlog-tab1 thead");

    cy.logout();
  });

  // TC.40: the events of the accreditation of the external organizations are
  // collected by the audit log. The registrations are performed by the signup
  // spec and the invitations by the sites one, both of which run before this.
  it("should list the events of the accreditation of the external organizations", () => {
    cy.login_admin();
    cy.visit("/#/admin/auditlog");

    // the events of the accreditation are searched by name: the column filter
    // of the Type column selects a severity, not an event type
    cy.get("#search-filter-input").should("be.visible").clear().type("signup");

    cy.get("src-auditlog-tab1 tbody tr").should("have.length.greaterThan", 0);
    cy.get("src-auditlog-tab1 tbody").should("contain", "signup");
    cy.takeScreenshot("admin/audit_log_signup_events");
    cy.takeScreenshot("admin/audit_log_signup_events_detail", "src-auditlog-tab1 table");

    cy.logout();
  });
});

describe("administrator sites list", () => {
  // TC.35: the administrator retrieves the address of a site from the list of
  // the sites, where it is offered as a link.
  it("should offer the link of a site in the list of the sites", () => {
    cy.login_admin();
    cy.visit("/#/admin/sites");
    cy.get(".tenant-badge a").first().should("be.visible").and("have.attr", "href");

    cy.takeScreenshot("admin/sites");
    cy.takeScreenshot("admin/sites_link_detail", ".tenant-badge:first");

    cy.logout();
  });
});

// A panel of the report renders its body only when it is open: capturing it
// closed produces a strip a few pixels tall with nothing in it
const expandPanel = (selector: string) => {
  cy.get(selector).should("be.visible").then(($panel) => {
    if ($panel.find(".card-body, .card-header + *").length === 0 ||
        $panel.find("[aria-expanded='false']").length > 0) {
      cy.get(`${selector} .card-header`).click();
    }
  });
};

describe("deletion protected by the confirmation modal", () => {
  // TC.36.1 and TC.36.2: the deletion of a user states what is being deleted.
  // The counts are shown only for a user that has reports, so the capture is
  // taken here and not where the users are configured: at that point of the
  // suite no report exists yet and the modal would have nothing to state.
  // TC.36.3: when the state changed while the modal was open the server refuses
  // with a 409 and the interface says so instead of deleting. The race cannot be
  // produced deterministically, so the refusal is imposed on the transport: what
  // is verified is the behaviour of the interface in front of it.
  it("should state what is deleted and refuse a deletion whose state changed", () => {
    cy.login_admin();
    cy.openAdminUsers();

    // the buttons of a repeated row carry no id: they are reached by the action
    // they perform, on a chain no assertion breaks, so that Cypress re-runs the
    // query when the row is redrawn between the lookup and the click
    cy.contains(".userList", "Recipient").first().find("[data-action='edit']").click();
    cy.contains(".userList", "Recipient").first().find("[data-action='delete']").click();

    cy.get(".modal-title").should("be.visible");
    cy.contains(".modal-body", "Reports").should("be.visible");
    cy.takeScreenshot("admin/user_delete_confirmation");
    cy.takeScreenshot("admin/user_delete_confirmation_detail", ".modal-dialog");

    // the deletion is confirmed with the administrator password before the
    // request leaves the browser: the refusal is imposed on that request
    cy.intercept("DELETE", "/api/admin/users/*", {statusCode: 409, body: {}}).as("refusedDeletion");
    cy.get("#modal-action-ok").click();
    cy.get(".modal [type='password']").should("be.visible").type(Cypress.env("user_password"));
    cy.get(".modal .btn-primary").click();
    cy.wait("@refusedDeletion");

    cy.contains(".modal-body", "Deletion prevented").should("be.visible");
    cy.takeScreenshot("admin/user_delete_prevented_detail", ".modal-dialog");

    // the user is not deleted: the operation is abandoned
    cy.get("#modal-action-cancel").click();
    cy.contains(".userList", "Recipient").should("exist");

    cy.logout();
  });

  // TC.37.1, TC.37.2 and TC.37.3: the same protection on the deletion of a site.
  // Platform F has received a report by this point of the suite, so the modal
  // has something to state; the site is not deleted, the operation is abandoned.
  it("should state what is deleted and refuse the deletion of a site whose state changed", () => {
    cy.login_admin();
    cy.visit("/#/admin/sites");
    cy.get('[data-cy="sites"]').click();

    // the row of a site is the shared list item: its delete carries the action
    // it performs, not a name of its own
    cy.contains("form", "Platform F").find("[data-action='delete']").click();

    cy.get(".modal-title").should("be.visible");
    cy.takeScreenshot("admin/tenant_delete_confirmation");
    cy.takeScreenshot("admin/tenant_delete_confirmation_detail", ".modal-dialog");

    cy.intercept("DELETE", "/api/admin/tenants/*", {statusCode: 409, body: {}}).as("refusedTenantDeletion");
    cy.get("#modal-action-ok").click();
    cy.get(".modal [type='password']").should("be.visible").type(Cypress.env("user_password"));
    cy.get(".modal .btn-primary").click();
    cy.wait("@refusedTenantDeletion");

    cy.contains(".modal-body", "Deletion prevented").should("be.visible");
    cy.takeScreenshot("admin/tenant_delete_prevented_detail", ".modal-dialog");

    cy.get("#modal-action-cancel").click();
    cy.contains("form", "Platform F").should("exist");

    cy.logout();
  });
});

describe("report audit log and read receipts", () => {
  // TC.29: the audit log of a report is reachable and lists the operations
  // performed on it.
  // TC.30: among them the upload of the attachments and the accesses to them.
  it("should list the operations on the report and on its files", () => {
    cy.login_receiver();
    cy.visit("/#/recipient/reports");
    cy.waitForUrl("/recipient/reports");
    cy.get("#tip-0").first().click();
    cy.get("#TipInfoBox").should("be.visible");

    cy.takeScreenshot("admin/report_audit_log_button_detail", "#TipToolbar");

    // The chapter on the file events needs a log that contains them: a report
    // without attachments produces none, so one is attached and downloaded here
    // and the log is then filtered on those very events.
    expandPanel("#TipPageRFileUpload");
    cy.get("#upload_description").first().should("be.visible").type("attachment of the recipient");
    cy.get('input[type="file"]').selectFile("./cypress/fixtures/files/test.txt", {force: true});
    cy.get(".download-button").first().click();

    cy.get("#tip-action-access-audit-log").click();
    cy.get(".modal").should("be.visible");
    cy.takeScreenshot("admin/report_audit_log", ".modal-dialog");

    cy.get(".modal input[placeholder*='Search']").first().should("be.visible").type("file");
    cy.contains(".modal", "file").should("be.visible");
    cy.takeScreenshot("admin/report_audit_log_files");
    cy.takeScreenshot("admin/report_audit_log_files_detail", ".modal-dialog");
    cy.get("#modal-action-cancel").click();

    cy.logout();
  });

  // TC.31: the read receipt on the comments and on the files tells the sender
  // that the counterpart has seen what was sent.
  it("should show the read receipt on the comments and on the files", () => {
    // The receipt appears on a message only once the counterpart has read it,
    // so the exchange is built here in both directions instead of relying on
    // the order in which other specs happen to leave the reports: a report is
    // filed, the recipient writes on it, the whistleblower reads.
    pages.WhistleblowerPage.performSubmission(0).then((receipt) => {
      cy.login_receiver();
      cy.visit("/#/recipient/reports");
      cy.waitForUrl("/recipient/reports");
      cy.get("#tip-0").first().click();

      expandPanel("#TipCommentsBox");
      cy.get("[name='newCommentContent']").should("be.visible").type("Answer of the recipient");
      cy.get("#comment-action-send").click();
      cy.get("#comment-0").should("contain", "Answer of the recipient");
      cy.logout();

      // reading is what makes the receipt appear on the other side
      cy.login_whistleblower(String(receipt));
      cy.get("#TipInfoBox").should("be.visible");
      expandPanel("#TipCommentsBox");
      cy.get("#comment-0").should("contain", "Answer of the recipient");
      cy.logout();

      cy.login_receiver();
      cy.visit("/#/recipient/reports");
      cy.waitForUrl("/recipient/reports");
      cy.get("#tip-0").first().click();
    });

    // the panels open on their own body: a capture of a closed panel shows the
    // header alone, and one without comments shows nothing of what is described
    expandPanel("#TipCommentsBox");
    cy.get("#SubmissionComments").should("be.visible");
    cy.get("#comment-0").should("exist");
    cy.get("#TipCommentsBox .fa-check.text-success").should("exist");

    cy.takeScreenshot("recipient/tip_comments_read_receipt", "#TipCommentsBox");
    cy.takeScreenshot("recipient/tip_comments_read_receipt_detail", "#SubmissionComments");

    expandPanel("#TipPageFilesInfoBox");
    cy.get("#TipPageFilesInfoBox").should("be.visible");
    cy.takeScreenshot("recipient/tip_files_read_receipt_detail", "#TipPageFilesInfoBox");

    cy.visit("/#/recipient/reports");
    cy.waitForUrl("/recipient/reports");
    cy.get("#tip-0").should("be.visible");
    cy.takeScreenshot("recipient/tips_read_receipt_detail", "#TipList");

    cy.logout();
  });

  // TC.33: the recipient restricts the list to the reports that are new or
  // have been updated since the last access.
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

  // TC.34: the recipient sees how many recipients have access to a report and,
  // hovering the count, which ones.
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
  // TC.26, TC.27 and TC.28: what is deleted from a report leaves in the audit
  // log of the report the fingerprints of what has been taken away. The entry
  // is read by the recipient on its own copy and by the whistleblower on the
  // report it holds the receipt of, and by nobody else.
  it("should keep on the log the fingerprints of a deleted attachment", () => {
    pages.WhistleblowerPage.performSubmission(1).then((receipt) => {
      cy.login_receiver();
      cy.visit("/#/recipient/reports");
      cy.waitForUrl("/recipient/reports");
      cy.get("#tip-0").first().click();
      cy.get("#TipInfoBox").should("be.visible");

      // the deletion of an attachment lives in the masking mode: a file is
      // masked first, and the masked file is the one that can be redacted away
      cy.get("#actionsDropdownButton").click();
      cy.get("#tip-action-mask").click();

      cy.get("#ReportAttachments .fa-eraser").first().click();
      cy.get("#ReportAttachments .tip-action-delete-file").should("be.visible").first().click();

      cy.get("#tip-action-access-audit-log").click();
      cy.get(".modal").should("be.visible");
      cy.contains(".modal", "delete_file").should("be.visible");
      cy.get(".modal .audit-fingerprint code").should("be.visible");

      cy.takeScreenshot("recipient/report_audit_log_hashes");
      cy.takeScreenshot("recipient/report_audit_log_hashes_detail", ".modal-dialog");

      cy.get("#modal-action-cancel").click();
      cy.logout();

      // the same entry reaches the whistleblower on the report it filed
      cy.login_whistleblower(String(receipt));
      cy.get("#TipInfoBox").should("be.visible");
      cy.get("#tip-action-access-audit-log").click();
      cy.get(".modal").should("be.visible");
      cy.contains(".modal", "delete_file").should("be.visible");
      cy.get(".modal .audit-fingerprint code").should("be.visible");

      cy.takeScreenshot("whistleblower/report_audit_log_hashes");
      cy.takeScreenshot("whistleblower/report_audit_log_hashes_detail", ".modal-dialog");

      cy.get("#modal-action-cancel").click();
      cy.logout();
    });
  });
});
