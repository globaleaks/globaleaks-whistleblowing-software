import {PageIdleDetector} from "./PageIdleDetector";

declare global {
  namespace Cypress {
    interface Chainable {
      // @ts-ignore
      waitForLoader: () => void;
      waitForPageIdle: () => void;
      logout: () => void;
      takeScreenshot: (filename: string, locator?: string) => void;
      login_whistleblower: (receipt: string) => void;
      waitForTipImageUpload: (attempt?: number) => void;
      waitUntilClickable: (locator: string, timeout?: number) => void;
      waitForUrl: (url: string, timeout?: number) => Chainable<any>;
      login_admin: (username?: string, password?: string, url?: string, firstlogin?: boolean) => void;
      login_receiver: (username?: string, password?: string, url?: string, firstlogin?: boolean) => void;
      simple_login_receiver: (username?: string, password?: string, url?: string, firstlogin?: boolean) => void;
      simple_login_admin: (username?: string, password?: string, url?: string, firstlogin?: boolean) => void;
      login_custodian: (username?: string, password?: string, url?: string, firstlogin?: boolean) => void;
      login_analyst: (username?: string, password?: string, url?: string, firstlogin?: boolean) => void;
      login_accreditor: (username?: string, password?: string, url?: string, firstlogin?: boolean) => void;
      request_external_organization: (denomination?: string, pec?: string, url?: string, adminTaxCode?: string) => void;
      confirm_accreditation_request: (reqId: string) => void;
    }
  }
}

Cypress.Commands.add("confirm_accreditation_request", (reqId) => {

  cy.visit("#/accreditation-request/"+reqId);

  cy.get('input[name="privacyAccept"]').click();

  cy.get("#proceed").should("be.enabled");
  cy.get("#proceed").click();

  cy.wait(1000);
  
  cy.get(".modal").should("be.visible");
  cy.get(".modal #closeConfirmModal").click();

});

Cypress.Commands.add("request_external_organization", (denomination, pec, url, adminTaxCode) => {

  denomination = denomination === undefined ? "Organizzazione 1" : denomination;
  pec = pec === undefined ? "example@examplepec.com" : pec;
  url = url === undefined ? "http://exampleurl.com" : url;
  adminTaxCode = adminTaxCode === undefined ? "LLNBRY89A18D969M" : adminTaxCode;


  cy.setCookie("x-idp-userid", adminTaxCode);
  cy.visit('/#/accreditation-request');

  cy.get('input[name="denomination"]').type(denomination);
  cy.get('input[name="pec"]').type(pec);
  cy.get('input[name="confirmPec"]').type(pec);
  cy.get('input[name="institutionalWebsite"]').type(url);

  cy.get('input[name="adminName"]').type("Barry");
  cy.get('input[name="adminSurname"]').type("Allen");

  cy.get('input[name="adminTaxCode"]').invoke('val').should('not.be.empty');

  cy.get('input[name="adminEmail"]').type("example@example.com");
  cy.get('input[name="adminTaxCode"]').should("be.disabled");

  cy.get('input[name="recipientName"]').type("Clark");
  cy.get('input[name="recipientSurname"]').type("Kent");
  cy.get('input[name="recipientTaxCode"]').type("KNTCRK91S11I480G");
  cy.get('input[name="recipientEmail"]').type("example1@example1.com");

  cy.get('input[name="privacyAccept"]').click();

  cy.get("#proceed").should("be.enabled");
  cy.get("#proceed").click();

  cy.wait(1000);
  
  cy.get(".modal").should("be.visible");
  cy.get(".modal #closeConfirmModal").click();

});


Cypress.Commands.add("waitForPageIdle", () => {
  const pageIdleDetector = new PageIdleDetector();
  pageIdleDetector.waitForPageToBeIdle();
  cy.wait(0);
});

Cypress.Commands.add("login_receiver", (username, password, url, firstlogin) => {
  username = username === undefined ? "Recipient" : username;
  password = password === undefined ? Cypress.env("user_password") : password;
  url = url === undefined ? "#/login" : url;

  let finalURL = "/actions/forcedpasswordchange";

  cy.visit(url);
  cy.get("[name=\"username\"]").type(username);

  // @ts-ignore
  cy.get("[name=\"password\"]").type(password);
  cy.get("#login-button").click();

  if (!firstlogin) {
    cy.url().should("include", "#/login").then(() => {
      cy.url().should("not.include", "#/login").then((currentURL) => {
        const hashPart = currentURL.split("#")[1];
        finalURL = hashPart === "login" ? "/recipient/home" : hashPart;
        cy.waitForUrl(finalURL);
      });
    });
  }

  cy.waitForPageIdle();
});

Cypress.Commands.add("simple_login_receiver", (username, password, url, firstlogin) => {
  username = username === undefined ? "Recipient" : username;
  password = password === undefined ? Cypress.env("user_password") : password;
  url = url === undefined ? "#/login" : url;

  let finalURL = "/actions/forcedpasswordchange";

  cy.visit(url);
  cy.get('ng-select[name="authentication.loginData.loginUsername"]').click(); 
  cy.get('.ng-option').first().click();

  // @ts-ignore
  
  cy.get("[name=\"password\"]").type(password);
  cy.get("#login-button").click();

  if (!firstlogin) {
    cy.url().should("include", "#/login").then(() => {
      cy.url().should("not.include", "#/login").then((currentURL) => {
        const hashPart = currentURL.split("#")[1];
        finalURL = hashPart === "login" ? "/recipient/home" : hashPart;
        cy.waitForUrl(finalURL);
      });
    });
  }

  cy.waitForPageIdle();
});

Cypress.Commands.add("simple_login_admin", (username, password, url, firstlogin) => {
  username = username === undefined ? "admin" : username;
  password = password === undefined ? Cypress.env("user_password") : password;
  url = url === undefined ? "#/admin" : url;

  let finalURL = "";

  cy.visit(url);

  cy.get("[name=\"username\"]").type(username);

  // @ts-ignore
  cy.get("[name=\"password\"]").type(password);
  cy.get("#login-button").click();

  if (firstlogin) {
    finalURL = "/actions/forcedpasswordchange";
    cy.waitForUrl(finalURL);
  } else {
    cy.url().should("include", "#/admin").then((_) => {
      cy.url().should("not.include", "#/login").then((currentURL) => {
        const hashPart = currentURL.split("#")[1];
        finalURL = hashPart === "login" ? "/admin/home" : hashPart;
      });
    });
    cy.waitForLoader()
  }
});

Cypress.Commands.add("login_analyst", (username, password, url, firstlogin) => {
  username = username === undefined ? "Analyst" : username;
  password = password === undefined ? Cypress.env("user_password") : password;
  url = url === undefined ? "#/login" : url;

  let finalURL = "/actions/forcedpasswordchange";

  cy.visit(url);
  cy.get("[name=\"username\"]").type(username);

  // @ts-ignore
  cy.get("[name=\"password\"]").type(password);
  cy.get("#login-button").click();

  if (!firstlogin) {
    cy.url().should("include", "#/login").then(() => {
      cy.url().should("not.include", "#/login").then((currentURL) => {
        const hashPart = currentURL.split("#")[1];
        finalURL = hashPart === "login" ? "/analyst/home" : hashPart;
        cy.waitForUrl(finalURL);
      });
    });
  }

  cy.waitForPageIdle();
});

Cypress.Commands.add("login_custodian", (username, password, url, firstlogin) => {
  username = username === undefined ? "Custodian" : username;
  password = password === undefined ? Cypress.env("user_password") : password;
  url = url === undefined ? "#/login" : url;

  let finalURL = "/actions/forcedpasswordchange";

  cy.visit(url);
  cy.get("[name=\"username\"]").type(username);
  // @ts-ignore
  cy.get("[name=\"password\"]").type(password);
  cy.get("#login-button").click();

  if (!firstlogin) {
    cy.url().should("include", "/login").then(() => {
      cy.url().should("not.include", "/login").then((currentURL) => {
        const hashPart = currentURL.split("#")[1];
        finalURL = hashPart === "login" ? "/custodian/home" : hashPart;
        cy.waitForUrl(finalURL);
      });
    });
  }

});

Cypress.Commands.add("login_accreditor", (username, password, url, firstlogin) => {
  username = username === undefined ? "Resp_Accreditation" : username;
  password = password === undefined ? Cypress.env("user_password") : password;
  url = url === undefined ? "#/login" : url;

  let finalURL = "/actions/forcedpasswordchange";

  cy.visit(url);
  cy.get("[name=\"username\"]").type(username);

  // @ts-ignore
  cy.get("[name=\"password\"]").type(password);
  cy.get("#login-button").click();

  if (!firstlogin) {
    cy.url().should("include", "#/login").then(() => {
      cy.url().should("not.include", "#/login").then((currentURL) => {
        const hashPart = currentURL.split("#")[1];
        finalURL = hashPart === "login" ? "/accreditor/home" : hashPart;
        cy.waitForUrl(finalURL);
      });
    });
  }

  cy.waitForPageIdle();
});

Cypress.Commands.add("takeScreenshot", (filename: string, locator?: string) => {
  if (!Cypress.env("takeScreenshots")) {
    return;
  }

  cy.get("html, body").invoke(
    "attr",
    "style",
    "height: auto;"
  );

  if (locator == '.modal') {
    cy.get(".modal").invoke(
      "attr",
      "style",
      "height: auto; position: absolute;"
    );
  }

  return cy.document().then((doc) => {
    cy.viewport(1920, doc.body.scrollHeight);

    cy.waitForPageIdle();

    cy.wait(500);

    if (locator && locator !== ".modal") {
      return cy.get(locator).screenshot("../" + filename, {overwrite: true, scale: true});
    }

    return cy.screenshot("../" + filename, {
      capture: "fullPage",
      overwrite: true,
      scale: true
    });
  });
});

Cypress.Commands.add("waitUntilClickable", (locator: string, timeout?: number) => {
  const t = timeout === undefined ? Cypress.config().defaultCommandTimeout : timeout;
  cy.get(locator).click({timeout: t});
});

Cypress.Commands.add("waitForLoader", () => {
  cy.intercept("**").as("httpRequests");

  cy.get('[data-cy="page-loader-overlay"]', {timeout: 500, log: false})
    .should(($overlay) => {
      return new Cypress.Promise((resolve, _) => {
        const startTime = Date.now();

        const checkVisibility = () => {
          if (Cypress.$($overlay).is(":visible")) {
            cy.get('[data-cy="page-loader-overlay"]', { log: false }).should("not.be.visible").then(() => {
              resolve();
            });
          } else if (Date.now() - startTime > 100) {
            resolve();
          } else {
            setTimeout(checkVisibility, 100);
          }
        };

        checkVisibility();
      });
    })
});


Cypress.Commands.add("waitForUrl", (url: string, timeout?: number) => {
  const t = timeout === undefined ? Cypress.config().defaultCommandTimeout : timeout;
  return cy.url().should("include", url, {timeout: t});
});

Cypress.Commands.add("login_whistleblower", (receipt) => {
  cy.visit("/");

  cy.get('[name="receipt"]').type(receipt);
  cy.get("#ReceiptButton").click();
});

Cypress.Commands.add("waitForTipImageUpload", (attempts = 0) => {
  const maxAttempts = 10;
  cy.get('body').then($body => {
    if ($body.find('#fileListBody').length > 0) {
      cy.get('#fileListBody')
        .find('tr')
        .then($rows => {
          if ($rows.length === 2) {
            cy.log('Condition met: 2 rows found');
          } else if (attempts < maxAttempts) {
            cy.get('#link-reload').click();
            cy.wait(1000);
            cy.waitForTipImageUpload(attempts + 1);
          }
        });
    } else if (attempts < maxAttempts) {
      cy.get('#link-reload').click();
      cy.wait(1000);
      cy.waitForTipImageUpload(attempts + 1);
    }
  });
});

Cypress.Commands.add("login_admin", (username, password, url, firstlogin) => {
  username = username === undefined ? "admin" : username;
  password = password === undefined ? Cypress.env("user_password") : password;
  url = url === undefined ? "#/login" : url;

  let finalURL = "";

  cy.visit(url);

  cy.get("[name=\"username\"]").type(username);

  // @ts-ignore
  cy.get("[name=\"password\"]").type(password);
  cy.get("#login-button").click();

  if (firstlogin) {
    finalURL = "/actions/forcedpasswordchange";
    cy.waitForUrl(finalURL);
  } else {
    cy.url().should("include", "#/login").then((_) => {
      cy.url().should("not.include", "#/login").then((currentURL) => {
        const hashPart = currentURL.split("#")[1];
        finalURL = hashPart === "login" ? "/admin/home" : hashPart;
        cy.waitForUrl(finalURL);
      });
    });
    cy.waitForLoader()
  }
});

Cypress.Commands.add("logout", () => {
  cy.get('#LogoutLink').should('be.visible').click();
});
