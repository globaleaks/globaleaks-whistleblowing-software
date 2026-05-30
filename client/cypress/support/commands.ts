declare global {
  namespace Cypress {
    interface Chainable {
      // @ts-ignore
      login_admin: (username?: string, password?: string, url?: string, firstlogin?: boolean) => void;
      login_analyst: (username?: string, password?: string, url?: string, firstlogin?: boolean) => void;
      login_receiver: (username?: string, password?: string, url?: string, firstlogin?: boolean) => void;
      login_custodian: (username?: string, password?: string, url?: string, firstlogin?: boolean) => void;
      login_whistleblower: (receipt: string) => void;
      logout: () => void;
      simple_login_admin: (username?: string, password?: string, url?: string, firstlogin?: boolean) => void;
      simple_login_receiver: (username?: string, password?: string, url?: string, firstlogin?: boolean) => void;
      takeScreenshot: (filename: string, locator?: string) => void;
      waitForTipImageUpload: (attempt?: number) => void;
      waitForUrl: (url: string, timeout?: number) => Chainable<any>;
      waitUntilClickable: (locator: string, timeout?: number) => void;
    }
  }
}

// Define at the top of the spec file or just import it
function terminalLog(violations) {
  cy.task(
    'log',
    `${violations.length} accessibility violation${
      violations.length === 1 ? '' : 's'
    } ${violations.length === 1 ? 'was' : 'were'} detected`
  )
  // pluck specific keys to keep the table readable
  const violationData = violations.map(
    ({ id, impact, description, nodes }) => ({
      id,
      impact,
      description,
      nodes: nodes.length
    })
  )

  cy.task('table', violationData)
}

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
});

Cypress.Commands.add("login_whistleblower", (receipt) => {
  cy.visit("/");

  cy.takeScreenshot("whistleblower/receipt_input", "#WhistleblowerLoginBox");

  cy.get('[name="receipt"]').type(receipt);
  cy.get("#ReceiptButton").click();
});

Cypress.Commands.add("logout", () => {
  cy.get('#LogoutLink').should('be.visible').click();
  cy.url().should((url) => {
    expect(url.includes("#/login") || url.startsWith("about:blank")).to.be.true;
  });
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
  }
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
});

Cypress.Commands.add("takeScreenshot", (filename: string, locator?: string) => {
  if (!Cypress.env("takeScreenshots")) {
    return;
  }

  return cy.document().then((doc) => {
    cy.injectAxe()
    cy.checkA11y(null, null, terminalLog, true);

    if (locator) {
      cy.viewport(1280, 1024);
      cy.wait(50);
      return cy.get(locator).should("be.visible").screenshot("../" + filename, {overwrite: true});
    }

    cy.wait(50);

    // Ensure the screenshot does not include signs of mouse position/clicks
    cy.get('body').click(0, 0);

    return cy.screenshot("../" + filename, {overwrite: true, scale: true });
  });
});

Cypress.Commands.add("waitForUrl", (url: string, timeout?: number) => {
  const t = timeout === undefined ? Cypress.config().defaultCommandTimeout : timeout;
  return cy.url().should("include", url, {timeout: t});
});


Cypress.Commands.add("waitUntilClickable", (locator: string, timeout?: number) => {
  const t = timeout === undefined ? Cypress.config().defaultCommandTimeout : timeout;
  cy.get(locator).click({timeout: t});
});
