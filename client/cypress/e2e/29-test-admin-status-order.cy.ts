import {t} from "../support/i18n";
// The statuses of the reports are listed in the order the administrator gives them
describe("order of the report statuses", () => {
  const statusLabels = () =>
    cy.get(".submissionStatus span[id^='status-']").then($spans =>
      $spans.toArray().map(span => span.textContent?.trim()));

  const addStatus = (label: string) => {
    cy.get(".show-add-user-btn").click();
    cy.get(".addSubmissionStatus").should("be.visible");
    cy.get('input[name="name"]').type(label);
    cy.intercept("POST", "**/api/admin/statuses").as("addStatus");
    cy.get("#add-btn").click();
    cy.wait("@addStatus").its("response.statusCode").should("be.within", 200, 299);
  };

  const deleteStatus = (label: string) => {
    cy.contains(".submissionStatus", label).within(() => {
      cy.get("[data-action='delete']").click();
    });
    cy.get("#modal-action-ok").click();
    cy.contains(".submissionStatus", label).should("not.exist");
  };

  // named apart from what earlier runs may have left behind
  const A = "Order A " + Date.now().toString().slice(-5);
  const B = "Order B " + Date.now().toString().slice(-5);

  it("should move a status among the custom ones, while the statuses of the system keep their place", () => {
    cy.login_admin();
    cy.visit("/#/admin/casemanagement");
    cy.get(".config-section").should("be.visible");

    addStatus(A);
    cy.contains(".submissionStatus", A).should("exist");
    addStatus(B);
    cy.contains(".submissionStatus", B).should("exist");

    // a status created is listed after the others, before Closed
    statusLabels().then(labels => {
      expect(labels.indexOf(A)).to.be.lessThan(labels.indexOf(B));
      expect(labels.indexOf(B)).to.eq(labels.indexOf(t("Closed")) - 1);
    });

    cy.intercept("PUT", "**/api/admin/statuses").as("reorder");
    cy.contains(".submissionStatus", B).within(() => {
      cy.get("[data-action='move-up']").click();
    });
    cy.wait("@reorder");

    // the order saved is the one the page lists on a fresh read
    cy.visit("/#/admin/home");
    cy.visit("/#/admin/casemanagement");
    cy.get(".config-section").should("be.visible");
    cy.contains(".submissionStatus", A).should("exist");
    statusLabels().then(labels => {
      expect(labels.indexOf(B)).to.be.lessThan(labels.indexOf(A));
    });
    cy.takeScreenshot("admin/report_statuses_reordered");

    // New, Opened and Closed keep their place, and no status passes them
    cy.contains(".submissionStatus", t("New")).find("[data-action='move-up']").should("be.disabled");
    cy.contains(".submissionStatus", t("New")).find("[data-action='move-down']").should("be.disabled");
    cy.contains(".submissionStatus", t("Opened")).find("[data-action='move-down']").should("be.disabled");
    cy.contains(".submissionStatus", t("Closed")).find("[data-action='move-up']").should("be.disabled");
    cy.contains(".submissionStatus", A).find("[data-action='move-down']").should("be.disabled");

    deleteStatus(B);
    deleteStatus(A);
    cy.logout();
  });
});
