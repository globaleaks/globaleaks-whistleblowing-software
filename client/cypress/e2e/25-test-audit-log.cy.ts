// The audit log is an administrative section behind can_manage_auditlog and the only section of the
// auditor
describe("auditor audit log", () => {
  it("should reach the audit log with the credentials of the auditor", () => {
    cy.login_auditor();

    cy.waitForUrl("/auditor/home");
    cy.get("#auditor_audit_log").click();
    cy.waitForUrl("/auditor/auditlog");

    cy.get("src-auditlog-tab1 tbody tr").should("have.length.greaterThan", 0);

    // photographed once by the capture spec: repeating the login here costs a whole session

    cy.logout();
  });

});

describe("administrator audit log", () => {
  // the administrator restricts the audit log to a range of dates.
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

  // the administrator restricts the audit log to a single user.
  it("should filter the audit log by user", () => {
    cy.login_admin();
    cy.visit("/#/admin/auditlog");
    cy.get("#filter-username").click();

    // a capture changes the viewport and closes the list: choose the user first, capture afterwards
    cy.contains("ng-multiselect-dropdown .multiselect-item-checkbox", "admin").click();

    cy.get("#filter-username").should("have.class", "filter-active");
    cy.takeScreenshot("admin/audit_log_user_filtered");

    // the heading toggles the list: open it only where the capture closed it
    cy.get("body").then(($body) => {
      if (!$body.find("ng-multiselect-dropdown .multiselect-item-checkbox:visible").length) {
        cy.get("#filter-username").click();
      }
    });
    cy.contains("ng-multiselect-dropdown .multiselect-item-checkbox", "admin").should("be.visible");
    cy.takeScreenshot("admin/audit_log_user_filter_detail", "src-auditlog-tab1 thead");

    cy.logout();
  });

  // The registrations and the invitations are performed by earlier specs
  it("should list the events of the accreditation of the external organizations", () => {
    cy.login_admin();
    cy.visit("/#/admin/auditlog");

    // searched by name: the Type filter selects a severity, not an event type
    cy.get("#search-filter-input").should("be.visible").clear().type("signup");

    cy.get("src-auditlog-tab1 tbody tr").should("have.length.greaterThan", 0);
    cy.get("src-auditlog-tab1 tbody").should("contain", "signup");
    cy.takeScreenshot("admin/audit_log_signup_events");
    cy.takeScreenshot("admin/audit_log_signup_events_detail", "src-auditlog-tab1 table");

    cy.logout();
  });
});

describe("administrator sites list", () => {
  it("should offer the link of a site in the list of the sites", () => {
    cy.login_admin();
    cy.visit("/#/admin/sites");
    cy.get(".tenant-badge a").first().should("be.visible").and("have.attr", "href");

    cy.takeScreenshot("admin/sites");
    cy.takeScreenshot("admin/sites_link_detail", ".tenant-badge:first");

    cy.logout();
  });
});

describe("deletion protected by the confirmation modal", () => {
  // the deletion of a user states what is being deleted.
  // The counts are shown only for a user with reports: captured here, not where the users are
  // configured
  // A state change while the modal is open makes the server refuse with 409; the race is imposed on
  // the transport
  it("should state what is deleted and refuse a deletion whose state changed", () => {
    cy.login_admin();
    cy.openAdminUsers();

    // the buttons of a repeated row carry no id: reached by action on an unbroken chain, re-run if
    // the row is redrawn
    cy.contains(".userList", "Recipient").first().find("[data-action='edit']").click();
    cy.contains(".userList", "Recipient").first().find("[data-action='delete']").click();

    cy.get(".modal-title").should("be.visible");
    cy.contains(".modal-body", "Reports").should("be.visible");
    cy.takeScreenshot("admin/user_delete_confirmation");
    cy.takeScreenshot("admin/user_delete_confirmation_detail", ".modal-dialog");

    // confirmed with the administrator password before the request leaves: the refusal is imposed on
    // that request
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

  // the same protection on the deletion of a site.
  // Platform F has a report by now, so the modal has something to state
  it("should state what is deleted and refuse the deletion of a site whose state changed", () => {
    cy.login_admin();
    cy.visit("/#/admin/sites");
    cy.get('[data-cy="sites"]').click();

    // the delete of the row carries the action, not a name
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
