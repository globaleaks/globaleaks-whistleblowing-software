import {computePalette} from "../../app/src/shared/theme/palette";

// The value a custom property takes on the root element, with the variables it names resolved:
// read again until it is the expected one, as the palette arrives with the public data
const expectRoot = (name: string, value: string) =>
  cy.document().should(doc => {
    expect(getComputedStyle(doc.documentElement).getPropertyValue(name).trim().toUpperCase(), name).to.eq(value.toUpperCase());
  });

const expectRoles = (roles: Record<string, string>) => {
  for (const [name, value] of Object.entries(roles)) {
    expectRoot(name, value);
  }
};

// The media features the browser reports, as the developer tools emulate them
const emulate = (features: {name: string; value: string}[]) =>
  cy.then(() => Cypress.automation("remote:debugger:protocol", {
    command: "Emulation.setEmulatedMedia",
    params: {media: "", features}
  }));

// A text of the interface in the language of the run, as the site serves it
const translated = (key: string) =>
  cy.request(`l10n/${Cypress.expose("language")}`).then(response => (response.body as Record<string, string>)[key] || key);

const OFFICIAL_LIGHT = {
  "--gl-bg": "#FFF",
  "--gl-header": "#FFF",
  "--gl-footer": "#F2F4F7",
  "--gl-band": "#1F1F1F",
  "--gl-button": "#025A9F",
  "--gl-button-hover": "#002445",
  "--gl-on-button": "#FFF",
  "--gl-link": "#025A9F",
  "--gl-surface-subtle": "#ECF5FE",
  "--gl-text": "#1F1F1F",
  "--gl-text-secondary": "#525964",
  "--gl-border": "#A5ACB6",
  "--gl-border-input": "#6E7783",
  "--gl-surface-subtle-border": "transparent",
  "--gl-focus": "#002445",
  "--gl-warning": "#FE3",
  "--gl-danger": "#E30310"
};

const OFFICIAL_DARK = {
  "--gl-bg": "#1F1F1F",
  "--gl-surface": "#1F1F1F",
  "--gl-header": "#1F1F1F",
  "--gl-footer": "#002445",
  "--gl-surface-subtle": "#002445",
  "--gl-text": "#F2F4F7",
  "--gl-text-secondary": "#A5ACB6",
  "--gl-link": "#7BBBFE",
  "--gl-button": "#7BBBFE",
  "--gl-button-hover": "#ECF5FE",
  "--gl-on-button": "#1F1F1F",
  "--gl-border": "#6E7783",
  "--gl-surface-subtle-border": "#0978CF",
  "--gl-focus": "#7BBBFE",
  "--gl-warning": "#FE3",
  "--gl-danger": "#FF8F90"
};

// The color the tests leave to the site, which the palette keeps as it is, and its roles
const magenta = computePalette("#A0124F");

const MAGENTA_LIGHT = {
  "--gl-bg": "#FFF",
  "--gl-header": "#FFF",
  "--gl-button": magenta.primary[3] as string,
  "--gl-button-hover": magenta.primary[4] as string,
  "--gl-link": magenta.primary[3] as string,
  "--gl-text-secondary": magenta.neutral[3] as string
};

const MAGENTA_DARK = {
  "--gl-bg": "#1F1F1F",
  "--gl-header": "#1F1F1F",
  "--gl-button": magenta.primary[1] as string,
  "--gl-link": magenta.primary[1] as string,
  "--gl-surface-subtle": magenta.primary[4] as string,
  "--gl-text": magenta.neutral[0] as string
};

// Every field of the tab, the value the test gives it and where the site shows it
const TEXTS = {
  "#project-name-input": "Example Organization",
  "#node-description": "The reporting site of the example organization",
  "#node-header-title": "Report a wrongdoing",
  "#node-presentation": "Welcome to the reporting site",
  "#node-whistleblowing-question": "Have you witnessed a wrongdoing?",
  "#whistleblowing-button-input": "File a report",
  "#node-disclaimer-text": "Read this before you report",
  "#footer-whistleblowing-policy": "/whistleblowing-policy",
  "#footer-privacy-policy": "https://www.globaleaks.org/privacy",
  "#node-footer": "Example Organization, Example Street 1"
};

describe("admin configure settings", () => {
  it("should configure the texts of the site", () => {
    const original: Record<string, string> = {};

    cy.login_admin();
    cy.visit("#/admin/settings");
    cy.intercept("PUT", "**/api/admin/node").as("saveNode");

    for (const [selector, value] of Object.entries(TEXTS)) {
      cy.get(selector).invoke("val").then(text => {
        original[selector] = text as string;
      });
      cy.get(selector).clear().type(value);
    }

    // An address that is neither local nor on https is refused
    cy.get("#footer-privacy-policy").clear().type("http://www.globaleaks.org/privacy").should("have.class", "is-invalid");
    cy.get("#footer-privacy-policy").clear().type(TEXTS["#footer-privacy-policy"]).should("not.have.class", "is-invalid");

    cy.get("#save_settings").click();
    cy.wait("@saveNode");
    cy.logout();

    cy.visit("/#/");
    cy.title().should("eq", `${TEXTS["#project-name-input"]} - ${TEXTS["#node-header-title"]}`);
    cy.get('meta[name="description"]').should("have.attr", "content", TEXTS["#node-description"]);
    cy.get("#ProjectTitle").should("contain", TEXTS["#project-name-input"]);
    cy.get("#Presentation").should("contain", TEXTS["#node-presentation"]);
    cy.get("#WhistleblowingQuestion").should("contain", TEXTS["#node-whistleblowing-question"]);
    cy.get("#Policies a").first().should("have.attr", "href", TEXTS["#footer-whistleblowing-policy"]);
    cy.get("#Policies a").last().should("have.attr", "href", TEXTS["#footer-privacy-policy"]);
    cy.get("#CustomFooter").should("contain", TEXTS["#node-footer"]);

    // The disclaimer stands between the button and the questionnaire
    cy.get("#WhistleblowingButton").should("contain", TEXTS["#whistleblowing-button-input"]).click();
    cy.get(".modal").should("contain", TEXTS["#node-disclaimer-text"]);
    cy.get("#modal-action-ok").click();
    cy.get(".modal").should("not.exist");

    // The texts go back to those of the wizard, which the next specs expect
    cy.login_admin();
    cy.visit("#/admin/settings");
    cy.then(() => {
      for (const [selector, value] of Object.entries(original)) {
        cy.get(selector).invoke("val", value).trigger("input");
      }
    });
    cy.get("#save_settings").click();
    cy.wait("@saveNode");
    cy.logout();
  });

  it("should configure the primary color", () => {
    cy.login_admin();
    cy.visit("#/admin/settings");

    cy.get("#primary-color").should("have.value", "#0978cf");
    cy.get("#reset-primary-color").should("be.disabled");
    cy.get("#pick-primary-color .primary-color-value").should("have.text", "#0978CF");

    // The picker sits unseen under its button, which shows the color as it is chosen
    cy.get("#primary-color").invoke("val", "#2e7d32").trigger("input", { force: true });
    cy.get("#pick-primary-color .primary-color-value").should("have.text", "#2E7D32");

    // Nothing reaches the site before the save
    expectRoot("--gl-primary-3", "#0978CF");

    cy.intercept("PUT", "**/api/admin/node").as("saveNode");
    cy.get("#save_settings").click();
    cy.wait("@saveNode").its("request.body.primary_color").should("eq", "#2E7D32");

    const green = computePalette("#2E7D32");
    expectRoot("--gl-primary-3", "#2E7D32");
    expectRoot("--gl-button", green.primary[3] as string);

    // #C2185B fails the 7:1 of its step: the site keeps it as chosen, and is colored with the
    // closest accessible one
    cy.get("#primary-color").invoke("val", "#c2185b").trigger("input", { force: true });
    cy.get("#save_settings").click();
    cy.wait("@saveNode").its("response.body.primary_color").should("eq", "#C2185B");

    const pink = computePalette("#C2185B");
    expectRoot(`--gl-primary-${pink.step + 1}`, pink.primary[pink.step] as string);
    cy.document().should(doc => {
      expect(getComputedStyle(doc.documentElement).getPropertyValue(`--gl-primary-${pink.step + 1}`).trim().toUpperCase()).not.to.eq("#C2185B");
    });

    // The color of the next tests
    cy.get("#primary-color").invoke("val", "#a0124f").trigger("input", { force: true });
    cy.get("#save_settings").click();
    cy.wait("@saveNode").its("response.body.primary_color").should("eq", "#A0124F");
    cy.logout();
  });
});

describe("theme", () => {
  afterEach(() => {
    emulate([]);
  });

  it("follows the theme of the browser, in the color of the site", () => {
    emulate([{name: "prefers-color-scheme", value: "light"}]);
    cy.visit("/");
    cy.get("#LogoBox img").should("have.attr", "src", "s/logo");
    cy.get("html").should("not.have.attr", "data-theme");
    cy.get("html").should("have.attr", "data-bs-theme", "light");
    expectRoot(`--gl-primary-${magenta.step + 1}`, "#A0124F");
    expectRoles(MAGENTA_LIGHT);

    // Following the browser, the page follows it while open
    emulate([{name: "prefers-color-scheme", value: "dark"}]);
    cy.get("html").should("not.have.attr", "data-theme");
    cy.get("html").should("have.attr", "data-bs-theme", "dark");
    expectRoles(MAGENTA_DARK);

    // The GlobaLeaks logo in negative, white on transparent
    cy.get("#LogoBox img").should("have.attr", "src", "s/logo-dark").and($img => {
      expect(($img[0] as HTMLImageElement).naturalWidth).to.be.greaterThan(0);
    });
    cy.request("s/logo-dark").its("headers.content-type").should("eq", "image/webp");
  });

  it("keeps the theme the user switches to for the session alone", () => {
    emulate([{name: "prefers-color-scheme", value: "light"}]);
    cy.visit("/");
    cy.get("html").should("not.have.attr", "data-theme");

    // The switch stands right of the language
    cy.get("#ThemeToggleBox").should("have.class", "order-3");
    translated("Switch to the dark theme").then(label => {
      cy.get("#ThemeToggle").should("have.attr", "aria-label", label).click();
    });
    cy.get("html").should("have.attr", "data-theme", "dark");
    translated("Switch to the light theme").then(label => {
      cy.get("#ThemeToggle").should("have.attr", "aria-label", label);
    });
    expectRoles(MAGENTA_DARK);

    // The choice lives in the storage of the session alone
    cy.window().then(win => {
      expect(win.sessionStorage.getItem("theme")).to.eq("dark");
      expect(Object.keys(win.localStorage).filter(key => /theme/i.test(key))).to.deep.eq([]);
      expect(win.document.cookie).not.to.match(/theme|dark/i);
    });

    // A new load of the page in the same session keeps it, whatever the browser prefers
    cy.reload();
    cy.get("html").should("have.attr", "data-theme", "dark");
    expectRoles(MAGENTA_DARK);

    // Switched back, the choice is kept as well
    cy.get("#ThemeToggle").click();
    cy.get("html").should("have.attr", "data-theme", "light");
    emulate([{name: "prefers-color-scheme", value: "dark"}]);
    expectRoles(MAGENTA_LIGHT);
    cy.window().its("sessionStorage").invoke("getItem", "theme").should("eq", "light");

    // A new session follows the browser again
    cy.window().then(win => win.sessionStorage.clear());
    cy.reload();
    cy.get("html").should("not.have.attr", "data-theme");
    expectRoles(MAGENTA_DARK);

    // For the recipients the switch is the only place of the choice: the preferences do not offer
    // it, and the choice is never kept in the account
    emulate([{name: "prefers-color-scheme", value: "light"}]);
    cy.login_receiver();
    cy.get("html").should("not.have.attr", "data-theme");
    expectRoles(MAGENTA_LIGHT);
    cy.visit("/#/recipient/preferences");
    cy.get("#PreferencesForm").should("be.visible");
    cy.get("#pref-theme-select").should("not.exist");

    cy.intercept("PUT", "**/api/user/preferences").as("savePreferences");
    cy.get("#ThemeToggle").click();
    cy.get("html").should("have.attr", "data-theme", "dark");
    expectRoles(MAGENTA_DARK);
    cy.get("#ThemeToggle").click();
    cy.get("html").should("have.attr", "data-theme", "light");
    cy.get("@savePreferences.all").should("have.length", 0);
    cy.logout();
  });

  it("stays readable in forced colors and stronger in increased contrast", () => {
    emulate([{name: "prefers-contrast", value: "more"}, {name: "prefers-color-scheme", value: "light"}]);
    cy.visit("/");
    expectRoles({"--gl-text-secondary": magenta.neutral[4] as string, "--gl-link": magenta.primary[4] as string, "--gl-border": magenta.neutral[2] as string});

    emulate([{name: "prefers-contrast", value: "more"}, {name: "prefers-color-scheme", value: "dark"}]);
    expectRoles({"--gl-text-secondary": magenta.neutral[0] as string, "--gl-border": magenta.neutral[2] as string});

    emulate([{name: "forced-colors", value: "active"}]);
    cy.window().its("matchMedia").then(matchMedia => {
      expect(matchMedia("(forced-colors: active)").matches).to.eq(true);
    });

    // What a color alone told apart is given a border when the browser replaces the colors
    for (const selector of ["#PrivacyBadge", "#WhistleblowingButton", "#ThemeToggle"]) {
      cy.get(selector).should($element => {
        const style = getComputedStyle($element[0] as Element);
        expect(style.borderTopStyle, selector).to.eq("solid");
        expect(parseFloat(style.borderTopWidth), selector).to.be.at.least(1);
      });
    }
  });
});

describe("admin reset settings", () => {
  it("should reset the primary color to the GlobaLeaks default", () => {
    cy.login_admin();
    cy.visit("#/admin/settings");

    cy.get("#primary-color").should("have.value", "#a0124f");
    cy.get("#reset-primary-color").click();
    cy.get("#primary-color").should("have.value", "#0978cf");
    cy.get("#pick-primary-color").should("have.focus");
    cy.get("#reset-primary-color").should("be.disabled");

    cy.intercept("PUT", "**/api/admin/node").as("saveNode");
    cy.get("#save_settings").click();
    cy.wait("@saveNode").its("response.body.primary_color").should("eq", "#0978CF");
    cy.logout();

    emulate([{name: "prefers-color-scheme", value: "light"}]);
    cy.visit("/");
    expectRoles(OFFICIAL_LIGHT);
    emulate([{name: "prefers-color-scheme", value: "dark"}]);
    expectRoles(OFFICIAL_DARK);
    emulate([]);
  });
});
