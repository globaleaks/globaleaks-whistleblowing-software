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
  "--gl-header": "#1D1F24",
  "--gl-button": "#02518F",
  "--gl-text": "#1D1F24",
  "--gl-danger": "#E30310"
};

const DARK = {
  "--gl-bg": "#1D1F24",
  "--gl-surface": "#2C313A",
  "--gl-header": "#2C313A",
  "--gl-text": "#F2F4F7",
  "--gl-link": "#66B1F7",
  "--gl-button": "#0978CF",
  "--gl-danger": "#FF8B8C"
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
