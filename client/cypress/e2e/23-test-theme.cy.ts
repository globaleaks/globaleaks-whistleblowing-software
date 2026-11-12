// The value a custom property takes on the root element, with the variables it names resolved
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

const LIGHT = {
  "--gl-bg": "#FFF",
  "--gl-header": "#FFF",
  "--gl-band": "#1F1F1F",
  "--gl-link": "#025A9F",
  "--gl-button": "#025A9F",
  "--gl-text": "#1F1F1F",
  "--gl-danger": "#E30310"
};

const DARK = {
  "--gl-bg": "#1F1F1F",
  "--gl-surface": "#1F1F1F",
  "--gl-surface-subtle": "#002445",
  "--gl-header": "#1F1F1F",
  "--gl-text": "#F2F4F7",
  "--gl-link": "#7BBBFE",
  "--gl-button": "#7BBBFE",
  "--gl-danger": "#FF8F90"
};

describe("theme", () => {
  afterEach(() => {
    emulate([]);
  });

  it("follows the theme of the browser", () => {
    emulate([{name: "prefers-color-scheme", value: "light"}]);
    cy.visit("/");
    cy.get("#LogoBox img").should("have.attr", "src", "s/logo");
    cy.get("html").should("not.have.attr", "data-theme");
    cy.get("html").should("have.attr", "data-bs-theme", "light");
    expectRoles(LIGHT);

    // Following the browser, the page follows it while open
    emulate([{name: "prefers-color-scheme", value: "dark"}]);
    cy.get("html").should("not.have.attr", "data-theme");
    cy.get("html").should("have.attr", "data-bs-theme", "dark");
    expectRoles(DARK);

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
    cy.get("#ThemeToggle").should("have.attr", "aria-label", "Switch to the dark theme").click();
    cy.get("html").should("have.attr", "data-theme", "dark");
    cy.get("#ThemeToggle").should("have.attr", "aria-label", "Switch to the light theme");
    expectRoles(DARK);

    // The choice lives in the storage of the session alone
    cy.window().then(win => {
      expect(win.sessionStorage.getItem("theme")).to.eq("dark");
      expect(Object.keys(win.localStorage).filter(key => /theme/i.test(key))).to.deep.eq([]);
      expect(win.document.cookie).not.to.match(/theme|dark/i);
    });

    // A new load of the page in the same session keeps it, whatever the browser prefers
    cy.reload();
    cy.get("html").should("have.attr", "data-theme", "dark");
    expectRoles(DARK);

    // Switched back, the choice is kept as well
    cy.get("#ThemeToggle").click();
    cy.get("html").should("have.attr", "data-theme", "light");
    emulate([{name: "prefers-color-scheme", value: "dark"}]);
    expectRoles(LIGHT);
    cy.window().its("sessionStorage").invoke("getItem", "theme").should("eq", "light");

    // A new session follows the browser again
    cy.window().then(win => win.sessionStorage.clear());
    cy.reload();
    cy.get("html").should("not.have.attr", "data-theme");
    expectRoles(DARK);
  });
});
