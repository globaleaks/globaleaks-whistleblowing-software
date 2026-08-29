import * as pages from '../support/pages';

describe("recipient exchange workflow", function () {
  let platformFUrl = "";

  const open_platform_f = () => {
    cy.login_admin();
    cy.visit("/#/admin/sites");
    cy.get('[data-cy="sites"]').click().should("be.visible").click();

    cy.intercept("GET", "/api/auth/tenantauthswitch/**").as("tenantAuthSwitch");
    cy.window().then((win: any) => {
      if (win.open.restore) {
        win.open.restore();
      }
      cy.stub(win, "open").as("windowOpen");
    });

    cy.contains("form", "Platform F").within(() => {
      cy.get("button[name='configure_tenant']").click();
    });

    cy.wait("@tenantAuthSwitch").then((interception: any) => {
      const redirectUrl = interception.response.body.redirect;
      platformFUrl = redirectUrl.split("#")[0].replace(/\/$/, "");

      cy.get("@windowOpen").should("be.calledWith", redirectUrl);
      cy.visit(redirectUrl);
      cy.waitForUrl("/admin/home");
    });

  };

  const fill_transmit_form = () => {
    cy.get("#TransmitForm").should("be.visible").then(($form) => {
      const selects = $form.find("select:visible");
      const inputs = $form.find('input:visible:not([type="hidden"]):not([type="file"]):not([type="checkbox"]):not([type="radio"])');
      const textareas = $form.find("textarea:visible");

      if (selects.length) {
        cy.wrap(selects).each(($select) => {
          cy.wrap($select).select(2);
        });
      }

      if (inputs.length) {
        cy.wrap(inputs).each(($input, index) => {
          cy.wrap($input).clear().type(`Transmission summary ${index + 1}`);
        });
      }

      if (textareas.length) {
        cy.wrap(textareas).each(($textarea, index) => {
          cy.wrap($textarea).clear().type(`Transmission detail ${index + 1}`);
        });
      }
    });
  };

  const clickReportAction = (actionSelector: string) => {
    cy.get("#actionsDropdownButton").scrollIntoView().should("be.visible").click({ force: true });
    // the action has to be offered: an exchange the platform does not allow
    // leaves the report without it and the workflow untested
    cy.get(actionSelector, { timeout: 10000 }).should("be.visible").click({ force: true });
  };

  // What a report holds is carried to another organization from the report
  // itself: it originates from it and is composed with the questionnaire of
  // the exchange
  const submitCommunication = (platformUrl, alias = 'communicatedReport') => {
    cy.intercept("POST", `${platformUrl}/api/recipient/rtips/**/communication*`).as(alias);
    fill_transmit_form();
    cy.get("#SubmitTransmitButton").scrollIntoView().should("be.visible").click();

    // the report is filed by the request: a refusal of the platform is a
    // failure of the workflow and not a step that passes unnoticed
    cy.wait(`@${alias}`).its("response.statusCode").should("eq", 200);
  };

  // The report filed on another site is filed by the site and not by one of
  // its reports: it originates from none and is composed from the list of them
  const submitTransmittedReport = (platformUrl, alias = 'transmittedReport') => {
    cy.intercept("POST", `${platformUrl}/api/recipient/rtips/transmission`).as(alias);
    fill_transmit_form();
    cy.get("#SubmitTransmitButton").scrollIntoView().should("be.visible").click();

    cy.wait(`@${alias}`).its("response.statusCode").should("eq", 200);
  };

  it("should open Platform F, create a report, and communicate it to root", function () {
    open_platform_f();

    cy.then(() => {
      pages.WhistleblowerPage.performSubmission(0, `${platformFUrl}/#/`);

      cy.login_receiver("Platform F Recipient", Cypress.env("user_password"), `${platformFUrl}/#/login`);
      cy.visit(`${platformFUrl}/#/recipient/reports`);
      cy.waitForUrl("/recipient/reports");
      cy.get("#tip-0").should("be.visible").first().click();
      cy.get("#TipInfoBox").should("be.visible");
      cy.get(".TipInfoContext").contains("Default");

      clickReportAction('#tip-action-communicate');
      submitCommunication(platformFUrl, 'communicatedReport');

      cy.logout();

      // the report reaches the recipients of the tenant that received it
      cy.login_receiver();
      cy.visit("/#/recipient/reports");
      cy.waitForUrl("/recipient/reports");
      cy.get("#tip-0").should("be.visible");
      cy.logout();
    });
  });

  it("should open Platform G and transmission a report to root upon a request", function () {
    let platformGUrl = "";

    const open_platform_g = () => {
      cy.login_admin();
      cy.visit("/#/admin/sites");
      cy.get('[data-cy="sites"]').click().should("be.visible").click();

      cy.intercept("GET", "/api/auth/tenantauthswitch/**").as("tenantAuthSwitchG");
      cy.window().then((win: any) => {
        if (win.open.restore) {
          win.open.restore();
        }
        cy.stub(win, "open").as("windowOpenG");
      });

      cy.contains("form", "Platform G").within(() => {
        cy.get("button[name='configure_tenant']").click();
      });

      cy.wait("@tenantAuthSwitchG").then((interception: any) => {
        const redirectUrl = interception.response.body.redirect;
        platformGUrl = redirectUrl.split("#")[0].replace(/\/$/, "");

        cy.get("@windowOpenG").should("be.calledWith", redirectUrl);
        cy.visit(redirectUrl);
        cy.waitForUrl("/admin/home");
      });
    };

    open_platform_g();

    cy.then(() => {
      cy.logout();

      cy.login_receiver("Platform G Recipient", Cypress.env("user_password"), `${platformGUrl}/#/login`);
      cy.visit(`${platformGUrl}/#/recipient/reports`);
      cy.waitForUrl("/recipient/reports");
      cy.wait(100);
      cy.get("#tip-action-transmit").should("be.visible").first().click();
      submitTransmittedReport(platformGUrl, 'requestReportG');
      cy.logout();

      // the request reaches the tenant it is addressed to
      cy.login_receiver();
      cy.visit("/#/recipient/reports");
      cy.waitForUrl("/recipient/reports");
      cy.get("#tip-0").should("be.visible");
      cy.logout();
    });
  });
});
