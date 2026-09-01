import * as pages from '../support/pages';

describe("recipient exchange workflow", function () {
  let platformFUrl = "";

  const open_platform_f = () => {
    cy.login_admin();
    cy.visit("/#/admin/sites");
    cy.get('[data-cy="sites"]').click();

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

  // Answers can reveal further mandatory fields: the fields are re-read after every pass
  const fill_visible_fields = () => {
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

  const fill_transmit_form = () => {
    // first pass: the initial questions; second: the ones the answers reveal. The redraw is not
    // instantaneous: the pause lets it happen
    fill_visible_fields();
    cy.wait(200);
    fill_visible_fields();
  };

  const clickReportAction = (actionSelector: string) => {
    cy.get("#actionsDropdownButton").scrollIntoView().should("be.visible").click();
    // the action must be offered, or the workflow is untested
    cy.get(actionSelector, { timeout: 10000 }).should("be.visible").click();
  };

  const submitCommunication = (platformUrl: string, alias = 'communicatedReport') => {
    cy.intercept("POST", `${platformUrl}/api/recipient/rtips/**/communication*`).as(alias);
    fill_transmit_form();
    cy.get("#SubmitTransmitButton").scrollIntoView().click();

    // a refusal is a failure, not a silent step
    cy.wait(`@${alias}`).then((interception: any) => {
      expect(interception.response.statusCode).to.be.within(200, 299);

      // the form closes and the page moves to the filed report: both are waited for, or the move
      // lands on top of what the test visits next
      cy.get(".modal").should("not.exist");
      cy.url().should("include", interception.response.body.id);
    });
  };

  // the external organization fills the questionnaire of the exchange.
  // the recipients of the Authority reach the channel that receives the
  // communications and find the communicated report there.
  it("should open Platform F, create a report, and communicate it to root", function () {
    open_platform_f();

    cy.then(() => {
      pages.WhistleblowerPage.performSubmission(0, `${platformFUrl}/#/`);

      cy.login_receiver("Platform F Recipient", Cypress.env("user_password"), `${platformFUrl}/#/login`);
      cy.visit(`${platformFUrl}/#/recipient/reports`);
      cy.waitForUrl("/recipient/reports");
      cy.get("#tip-0").first().click();
      cy.get("#TipInfoBox").should("be.visible");
      cy.get(".TipInfoContext").contains("Default");

      // the address is kept: the communication files a report and the first row changes
      cy.url().as("communicatingReportUrl");

      clickReportAction('#tip-action-communicate');

      // the modal opens before the questionnaire arrives: wait for its fields
      cy.get("#TransmitForm").find("input, select, textarea").should("have.length.greaterThan", 0);
      cy.get("#TransmitForm").should("be.visible");
      cy.takeScreenshot("forward/forward_form", ".modal-dialog");
      cy.takeScreenshot("forward/forward_form_attachment_detail", "#TransmitForm");

      submitCommunication(platformFUrl, 'communicatedReport');

      // the exchanges performed on a report are listed on the report itself
      cy.get("@communicatingReportUrl").then((url) => {
        cy.visit(String(url));
      });
      cy.get("#TipInfoBox").should("be.visible");
      cy.get("#TipCommunicationsBox").should("be.visible");
      cy.takeScreenshot("recipient/forwards_list_detail", "#TipCommunicationsBox");

      cy.logout();

      cy.login_receiver();
      cy.visit("/#/recipient/reports");
      cy.waitForUrl("/recipient/reports");
      cy.get("#tip-0").should("be.visible");

      cy.takeScreenshot("recipient/tips");
      cy.takeScreenshot("recipient/tips_forward_channel_detail", "#TipList");

      cy.get("#tip-0").click();
      cy.get("#TipInfoBox").should("be.visible");
      cy.takeScreenshot("recipient/forward_report");
      cy.takeScreenshot("recipient/forward_report_messages_detail", "#TipCommentsBox");

      cy.logout();
    });
  });
});

// Transmission workflow on Platform G: a request, its authorization, the report and the access of
// the reporting person
describe("transmission workflow upon a request", function () {
  let platformGUrl = "";

  const open_platform_g = () => {
    cy.login_admin();
    cy.visit("/#/admin/sites");
    cy.get('[data-cy="sites"]').click();

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

  const login_transmitter = () => {
    cy.login_receiver("Platform G Recipient", Cypress.env("user_password"),
                      `${platformGUrl}/#/login`);
  };

  // The questionnaire is the default one: answered by the kind of each field
  const fill_visible_fields = () => {
    // fields are re-read from the page after each pass; the pause lets the redraw bring in the
    // revealed questions
    cy.wait(200);
    cy.get("body").then(($body) => {
      const fields = $body.find("#TransmitForm input:visible, #TransmitForm select:visible, #TransmitForm textarea:visible") as unknown as JQuery<HTMLElement>;

      fields.each((_, el) => {
        const tag = el.tagName.toLowerCase();

        if (tag === "select") {
          if (!(el as HTMLSelectElement).value) {
            cy.wrap(el).select(1);
          }
          return;
        }

        if (tag === "textarea") {
          if (!(el as HTMLTextAreaElement).value) {
            cy.wrap(el).clear().type("Transmission detail");
          }
          return;
        }

        const input = el as HTMLInputElement;

        if (input.type === "checkbox" || input.type === "radio") {
          if (!input.checked) {
            cy.wrap(el).check({force: true});
          }
          return;
        }

        if (["text", "email", "tel", "number", "url"].includes(input.type) && !input.value) {
          cy.wrap(el).clear().type("Transmission summary");
        }
      });
    });
  };

  // A multi-step questionnaire is answered one step at a time and filed on the last
  const fill_transmit_form = () => {
    cy.get("#TransmitForm").should("be.visible");

    for (let step = 0; step < 8; step++) {
      fill_visible_fields();
      cy.get("body").then(($body) => {
        if ($body.find("#NextStepButton:visible").length) {
          cy.get("#NextStepButton").click();
        }
      });
    }

    cy.get("#SubmitTransmitButton").should("be.visible");
  };

  // A transmission is filed by the site from the transmissions interface, not from a report
  const submitTransmission = (alias: string) => {
    cy.intercept("POST", `${platformGUrl}/api/transmitter/transmissions`).as(alias);
    fill_transmit_form();
    cy.get("#SubmitTransmitButton").scrollIntoView().click();

    cy.wait(`@${alias}`).its("response.statusCode").should("be.within", 200, 299);

    // the form closes itself and navigates to the report: wait for it to be gone before moving on
    cy.get(".modal").should("not.exist");
    cy.visit(`${platformGUrl}/#/recipient/home`);
  };

  const openTransmitForm = () => {
    cy.visit(`${platformGUrl}/#/recipient/transmissions`);
    cy.waitForUrl("/recipient/transmissions");
    cy.get("#transmission-action-transmit").should("be.visible").click();
    // the modal opens before the questionnaire arrives: wait for its fields
    cy.get("#TransmitForm").find("input, select, textarea").should("have.length.greaterThan", 0);
    cy.get("#TransmitForm").should("be.visible");
  };

  const clickReportAction = (actionSelector: string) => {
    cy.get("#actionsDropdownButton").scrollIntoView().should("be.visible").click();
    cy.get(actionSelector, { timeout: 10000 }).should("be.visible").click();
  };

  // The newest request: the list is ordered by date
  const openNewestAuthorityReport = () => {
    cy.login_receiver();
    cy.visit("/#/recipient/reports");
    cy.waitForUrl("/recipient/reports");
    cy.get("#tip-0").should("be.visible").click();
    cy.get("#TipInfoBox").should("be.visible");
  };

  // the external organization asks the Authority for the authorization to file a report.
  // the requests it filed are listed in the transmissions interface
  it("should file a request from the transmissions interface", function () {
    open_platform_g();

    cy.then(() => {
      cy.logout();
      login_transmitter();

      // opened from the toolbar of the transmissions list, not from a report
      cy.visit(`${platformGUrl}/#/recipient/transmissions`);
      cy.waitForUrl("/recipient/transmissions");
      cy.takeScreenshot("forward/tips_request_button_detail", "#Toolbar");

      cy.get("#transmission-action-transmit").should("be.visible").click();
      // the modal opens before the questionnaire arrives: wait for its fields
      cy.get("#TransmitForm").find("input, select, textarea").should("have.length.greaterThan", 0);
      cy.get("#TransmitForm").should("be.visible");
      cy.takeScreenshot("forward/forward_request_form", ".modal-dialog");
      submitTransmission("firstRequest");

      // what it filed is traced in the transmissions interface
      cy.visit(`${platformGUrl}/#/recipient/transmissions`);
      cy.waitForUrl("/recipient/transmissions");
      cy.get("#TransmissionList tbody tr").should("have.length.greaterThan", 0);
      cy.takeScreenshot("forward/tips_list");
      cy.takeScreenshot("forward/tips_list_status_detail", "#TransmissionList");

      // a request is followed by the site that filed it. An ungranted request opens no
      // report: pick an open-able row
      cy.get("#TransmissionList tbody tr.tip-action-open").first().click();
      cy.get("#TipInfoBox").should("be.visible");
      cy.takeScreenshot("forward/forward_request_status_eo");
      cy.takeScreenshot("forward/forward_request_messages_detail", "#TipCommentsBox");

      cy.logout();
    });
  });

  // the recipients of the Authority talk with the external organization on the request and
  // deny it
  it("should let the recipients talk on a request and deny it", function () {
    openNewestAuthorityReport();

    cy.takeScreenshot("recipient/forward_request_status");

    cy.get("#TipCommentsBox").should("be.visible").within(() => {
      cy.get("[name='newCommentContent']").should("be.visible").type("Clarification requested by the Authority");
      cy.get("#comment-action-send").click();
      cy.get("#comment-0").should("contain", "Clarification requested by the Authority");
    });

    cy.get("#actionsDropdownButton").scrollIntoView().should("be.visible").click();
    cy.takeScreenshot("recipient/forward_request_actions_detail", "#TipToolbar");
    cy.get("#tip-action-deny-transmission").should("be.visible").click();

    // the modal performs the denial: confirm it
    cy.get("#modal-action-ok").click();
    cy.get(".modal").should("not.exist");

    cy.contains(".TipInfoSubmissionStatus", "Denied").should("be.visible");
    cy.get("#tip-action-deny-transmission").should("not.exist");

    cy.logout();
  });

  // the Authority authorizes a request and the external organization files the report.
  // the questionnaire is composed once the authorization is granted. The receipt
  // handed over and the access of the reporting person
  it("should authorize a request, transmit the report and hand over its access code", function () {
    let accessCode = "";
    let requestUrl = "";

    login_transmitter();
    openTransmitForm();
    submitTransmission("secondRequest");

    // the external organization writes on the request, so the read receipt has something to mark
    cy.visit(`${platformGUrl}/#/recipient/transmissions`);
    cy.waitForUrl("/recipient/transmissions");
    // an ungranted request opens no report: pick an open-able row
    cy.get("#TransmissionList tbody tr.tip-action-open").first().click();
    cy.get("#TipInfoBox").should("be.visible");

    // the address is kept: the access code lives on the request
    cy.url().then((url) => {
      requestUrl = url;
    });

    cy.get("#TipCommentsBox").should("be.visible").within(() => {
      cy.get("[name='newCommentContent']").should("be.visible").type("Motivation of the external organization");
      cy.get("#comment-action-send").click();
      cy.get("#comment-0").should("contain", "Motivation of the external organization");
    });
    cy.logout();

    // the Authority authorizes it, and reading it marks the message
    openNewestAuthorityReport();
    cy.get("#TipCommentsBox").should("be.visible");
    clickReportAction('#tip-action-authorize-transmission');
    // the modal grants the authorization: confirm it
    cy.get("#modal-action-ok").click();
    cy.get(".modal").should("not.exist");
    cy.get("#tip-action-authorize-transmission").should("not.exist");
    cy.logout();

    // the authorization opens the questionnaire of the report
    login_transmitter();
    openTransmitForm();
    submitTransmission("transmittedReport");

    // the receipt handed over to the reporting person lives on the
    // request that granted the transmission
    cy.then(() => {
      cy.visit(requestUrl);
    });
    cy.get("#TipInfoBox").should("be.visible");

    // the Authority read the motivation: the message carries its receipt
    cy.get("#TipCommentsBox .text-success .fa-check").should("exist");
    cy.takeScreenshot("forward/tip_comments_read_receipt");
    cy.takeScreenshot("forward/tip_comments_read_receipt_detail", "#TipCommentsBox");

    clickReportAction('#tip-action-access-code');
    cy.get("#AccessCode").should("be.visible");
    cy.takeScreenshot("forward/access_code");
    cy.takeScreenshot("forward/access_code_detail", ".modal-dialog");

    cy.get("#AccessCode").invoke("val").then((value) => {
      accessCode = String(value).replace(/\s/g, "");
    });

    cy.get("#close").click();
    cy.logout();

    // the reporting person reaches the transmitted report on the portal
    // of the Authority with the code the external organization handed over
    cy.then(() => {
      cy.login_whistleblower(accessCode);

      // the temporary receipt is spent by the access: a new one is handed over
      cy.get("#ReceiptCode", { timeout: 30000 }).should("be.visible");
      cy.takeScreenshot("whistleblower/forwarded_tip_receipt_change_detail", ".modal-dialog");
      cy.get("#modal-action-ok").click();

      cy.get("#TipInfoBox", { timeout: 30000 }).should("be.visible");
      cy.takeScreenshot("whistleblower/forwarded_tip");
    });
  });
});
