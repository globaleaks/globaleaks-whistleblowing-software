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

  it("should move a status up and down the list", () => {
    cy.login_admin();
    cy.visit("/#/admin/casemanagement");
    cy.get(".config-section").should("be.visible");

    addStatus(A);
    addStatus(B);

    statusLabels().then(labels => {
      expect(labels.indexOf(A)).to.be.lessThan(labels.indexOf(B));
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
    statusLabels().then(labels => {
      expect(labels.indexOf(B)).to.be.lessThan(labels.indexOf(A));
    });
    cy.takeScreenshot("admin/report_statuses_reordered");

    // only the statuses a report is born in, New and Opened, move down: Opened is moved and moved back
    cy.contains(".submissionStatus", t("Opened")).within(() => {
      cy.get("[data-action='move-down']").click();
    });
    cy.wait("@reorder");

    cy.visit("/#/admin/home");
    cy.visit("/#/admin/casemanagement");
    cy.get(".config-section").should("be.visible");
    statusLabels().then(labels => {
      expect(labels.indexOf(t("Opened"))).to.eq(2);
    });

    cy.contains(".submissionStatus", t("Opened")).within(() => {
      cy.get("[data-action='move-up']").click();
    });
    cy.wait("@reorder");

    cy.visit("/#/admin/home");
    cy.visit("/#/admin/casemanagement");
    cy.get(".config-section").should("be.visible");
    statusLabels().then(labels => {
      expect(labels.indexOf(t("Opened"))).to.eq(1);
    });

    deleteStatus(B);
    deleteStatus(A);
    cy.logout();
  });
});
