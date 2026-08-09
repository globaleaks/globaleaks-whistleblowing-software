import * as pages from '../support/pages';

describe("recipient forwarding workflow", function () {
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

  // The forwarding is configured by the administrators of the platform alone:
  // the relationship between the sites is written by the sites spec, and the
  // requests of forward are demanded by the first site only for the site that
  // exercises them
  const require_forward_requests_on_root = (required) => {
    cy.visit("/#/admin/sites");
    cy.get('[data-cy="relationships"]').click().should("be.visible").click();
    cy.get('input[name="reception-require-requests-1"]').should(required ? "not.be.checked" : "be.checked").click();
    if (required) {
      cy.get('select[name="reception-request-channel-1"]').select(1);
    }
    cy.get('button[name="save_reception"]').first().click();
  };

  const fill_forward_form = () => {
    cy.get("#ForwardForm").should("be.visible").then(($form) => {
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
          cy.wrap($input).clear().type(`Forward summary ${index + 1}`);
        });
      }

      if (textareas.length) {
        cy.wrap(textareas).each(($textarea, index) => {
          cy.wrap($textarea).clear().type(`Forward detail ${index + 1}`);
        });
      }
    });
  };

  const clickForwardAction = (actionSelector = "#tip-action-forward") => {
    cy.get("#actionsDropdownButton").scrollIntoView().should("be.visible").click({ force: true });
    // the action has to be offered: a forward the platform does not allow
    // leaves the report without it and the workflow untested
    cy.get(actionSelector, { timeout: 10000 }).should("be.visible").click({ force: true });
  };

  const submitForward = (platformUrl, alias = 'forwardReport') => {
    cy.intercept("POST", `${platformUrl}/api/recipient/rtips/**/forward*`).as(alias);
    fill_forward_form();
    cy.get("#SubmitForwardButton").scrollIntoView().should("be.visible").click();

    // the forward is performed by the request: a refusal of the platform is a
    // failure of the workflow and not a step that passes unnoticed
    cy.wait(`@${alias}`).its("response.statusCode").should("eq", 200);
  };

  it("should open Platform F, create a report, and forward it to root", function () {
    open_platform_f();

    cy.then(() => {
      pages.WhistleblowerPage.performSubmission(0, `${platformFUrl}/#/`);

      cy.login_receiver("Platform F Recipient", Cypress.env("user_password"), `${platformFUrl}/#/login`);
      cy.visit(`${platformFUrl}/#/recipient/reports`);
      cy.waitForUrl("/recipient/reports");
      cy.get("#tip-0").should("be.visible").first().click();
      cy.get("#TipInfoBox").should("be.visible");
      cy.get(".TipInfoContext").contains("Default");

      clickForwardAction('#tip-action-forward');
      submitForward(platformFUrl, 'forwardReport');

      cy.logout();

      // the report reaches the recipients of the tenant that received it
      cy.login_receiver();
      cy.visit("/#/recipient/reports");
      cy.waitForUrl("/recipient/reports");
      cy.get("#tip-0").should("be.visible");
      cy.logout();
    });
  });

  it("should open Platform G and request forwarding to root", function () {
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

    cy.login_admin();
    require_forward_requests_on_root(true);
    cy.logout();

    open_platform_g();

    cy.then(() => {
      cy.logout();

      cy.login_receiver("Platform G Recipient", Cypress.env("user_password"), `${platformGUrl}/#/login`);
      cy.visit(`${platformGUrl}/#/recipient/reports`);
      cy.waitForUrl("/recipient/reports");
      cy.wait(100);
      cy.get("#tip-action-request-forward").should("be.visible").first().click();
      submitForward(platformGUrl, 'forwardReportG');
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
