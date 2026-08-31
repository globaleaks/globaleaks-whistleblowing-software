export {};

declare global {
  namespace Cypress {
    interface Chainable<Subject = any> {
      // @ts-ignore
      login_admin: (username?: string, password?: string, url?: string, firstlogin?: boolean) => void;
      login_user: (username?: string, password?: string, url?: string, firstlogin?: boolean, home?: string) => void;
      login_analyst: (username?: string, password?: string, url?: string, firstlogin?: boolean) => void;
      login_receiver: (username?: string, password?: string, url?: string, firstlogin?: boolean) => void;
      login_custodian: (username?: string, password?: string, url?: string, firstlogin?: boolean) => void;
      login_auditor: (username?: string, password?: string, url?: string, firstlogin?: boolean) => void;
      login_whistleblower: (receipt: string) => void;
      logout: () => void;
      simple_login_admin: (username?: string, password?: string, url?: string, firstlogin?: boolean) => void;
      simple_login_receiver: (username?: string, password?: string, url?: string, firstlogin?: boolean) => void;
      takeScreenshot: (filename: string, locator?: string) => void;
      openAdminUsers: () => void;
      openTab: (name: string) => void;
      waitForPageIdle: (timeout?: number) => void;
      waitForTipImageUpload: (attempt?: number) => void;
      waitForUrl: (url: string, timeout?: number) => Chainable<any>;
      waitUntilClickable: (locator: string, timeout?: number) => void;
    }
  }
}

// Define at the top of the spec file or just import it
function terminalLog(violations: any[]) {
  cy.task(
    'log',
    `${violations.length} accessibility violation${
      violations.length === 1 ? '' : 's'
    } ${violations.length === 1 ? 'was' : 'were'} detected`
  )
  // pluck specific keys to keep the table readable
  const violationData = violations.map(
    ({ id, impact, description, nodes }: any) => ({
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

// The login of every role is the same sequence, written once
Cypress.Commands.add("login_user", (username, password, url, firstlogin, home) => {
  username = username === undefined ? "" : username;
  password = password === undefined ? Cypress.env("user_password") : password;
  url = url === undefined ? "#/login" : url;
  home = home === undefined ? "" : home;

  cy.visit(url);
  cy.get("[name=\"username\"]").type(username);
  // @ts-ignore
  cy.get("[name=\"password\"]").type(password);
  cy.get("#login-button").click();

  if (!firstlogin) {
    cy.url().should("include", "/login").then(() => {
      cy.url().should("not.include", "/login").then((currentURL) => {
        const hashPart = currentURL.split("#")[1];
        cy.waitForUrl(hashPart === "login" ? home : hashPart);
      });
    });
  }
});

Cypress.Commands.add("login_analyst", (username, password, url, firstlogin) => {
  cy.login_user(username === undefined ? "Analyst" : username, password, url, firstlogin, "/analyst/home");
});

Cypress.Commands.add("login_custodian", (username, password, url, firstlogin) => {
  cy.login_user(username === undefined ? "Custodian" : username, password, url, firstlogin, "/custodian/home");
});

Cypress.Commands.add("login_auditor", (username, password, url, firstlogin) => {
  cy.login_user(username === undefined ? "Auditor" : username, password, url, firstlogin, "/auditor/home");
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
  if (!Cypress.env("takeScreenshots")) return;

  const DESKTOP_VIEWPORT = { width: 1920, height: 1080 };

  if (locator === ".modal") {
    cy.get(".modal").invoke("attr", "style", "height: auto; position: absolute;");
  }

  // The two viewport changes that preceded the capture were what kept it from photographing a
  // transition
  cy.waitForPageIdle();
  cy.wait(200);

  return cy.document().then((doc) => {
    // The tallest of the four measures: an inner container that scrolls on its
    // own makes the body shorter than the page really is.
    const documentHeight = Math.max(
      doc.body.scrollHeight, doc.documentElement.scrollHeight,
      doc.body.offsetHeight, doc.documentElement.offsetHeight,
      DESKTOP_VIEWPORT.height
    );

    // The narrow capture is produced only on demand: no chapter of the manual
    // uses one, and taking it doubled the work of every single capture.
    const viewports: {width: number; height: number; prefix?: string}[] = [
      { width: DESKTOP_VIEWPORT.width, height: documentHeight },
      ...(Cypress.env("mobileScreenshots")
        ? [{ width: 375, height: 667, prefix: "mobile/" }]
        : [])
    ];

    // The accessibility scan runs only on request: on every capture it repeated the same findings
    if (Cypress.env("a11yOnScreenshots")) {
      cy.injectAxe();
      cy.checkA11y(undefined, undefined, terminalLog, true);
    }

    return cy.wrap(viewports).each((viewport: unknown) => {
      const { width, height, prefix } = viewport as {width: number; height: number; prefix?: string};
      // The viewport is set once, to the size of the document
      cy.viewport(width, height);
      cy.wait(50);

      const screenshotPath = prefix ? `${prefix}${filename}` : filename;

      if (locator && locator !== ".modal") {
        // A capture of a collapsed panel, of a hidden tab or of a duplicated identifier comes out a
        // few pixels tall. A modal is photographed with the backdrop around it, so that its border
        // and its rounded corners are seen: a capture cut on the box shows a bare white rectangle
        const padding = /modal/.test(locator) ? 16 : 0;
        return cy.get(locator)
          .should(($el) => {
            const box = $el[0].getBoundingClientRect();
            expect(box.width, `width of the capture ${screenshotPath} (${locator})`).to.be.greaterThan(16);
            expect(box.height, `height of the capture ${screenshotPath} (${locator})`).to.be.greaterThan(16);
          })
          .screenshot(screenshotPath, { overwrite: true, scale: true, padding });
      } else {
        // A full page capture stitches several scrolls: a modal, or anything fixed, breaks it
        return cy.screenshot(screenshotPath, {
          capture: prefix ? "fullPage" : "viewport",
          overwrite: true,
          scale: true
        });
      }
    }).then(() => {
      // Restore desktop viewport
      cy.viewport(DESKTOP_VIEWPORT.width, DESKTOP_VIEWPORT.height);
    });
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

// Clicking an active tab redraws the navigation and detaches the button: opened only when inactive
Cypress.Commands.add("openAdminUsers", () => {
  cy.intercept("GET", "/api/admin/users/profiles").as("adminUsersProfiles");
  cy.visit("/#/admin/users");
  cy.wait("@adminUsersProfiles");
  cy.waitForPageIdle();
});

Cypress.Commands.add("openTab", (name: string) => {
  cy.get(`[data-cy="${name}"]`).should("be.visible").then(($tab) => {
    if (!$tab.hasClass("active")) {
      cy.wrap($tab).click();
    }
  });
});

// The overlay covers the page while a request is in flight: its absence is the settled page
Cypress.Commands.add("waitForPageIdle", (timeout?: number) => {
  const t = timeout === undefined ? Cypress.config().defaultCommandTimeout : timeout;
  cy.get("#PageOverlay", {timeout: t}).should("not.exist");
});
