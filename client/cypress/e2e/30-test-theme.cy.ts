import {
  FIXED_COLORS,
  MINIMUMS,
  NEUTRAL_MINIMUMS,
  OFFICIAL_NEUTRAL,
  OFFICIAL_PRIMARY,
  computePalette,
  contrast,
  normalizeHexColor
} from "../../app/src/shared/theme/palette";

// The colors of the brand and of a few others, as an administrator would choose them
const COLORS = ["#2E7D32", "#6A1B9A", "#A0124F", "#E65100", "#00325C", "#FFD600", "#808080", "#FFFFFF", "#000000"];

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

const OFFICIAL_LIGHT = {
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

describe("palette", () => {
  it("is the official GlobaLeaks palette for the default color", () => {
    const palette = computePalette("#0978CF");
    expect(palette.primary).to.deep.eq(OFFICIAL_PRIMARY);
    expect(palette.neutral).to.deep.eq(OFFICIAL_NEUTRAL);
    expect(palette.exact).to.eq(true);

    // The palette of the Visual Identity Guidelines v3.0
    expect(OFFICIAL_PRIMARY).to.deep.eq(["#ECF5FE", "#7BBBFE", "#0978CF", "#025A9F", "#002445"]);
    expect(OFFICIAL_NEUTRAL).to.deep.eq(["#F2F4F7", "#A5ACB6", "#6E7783", "#525964", "#1F1F1F"]);
  });

  it("computes from the official color a palette close to the official one", () => {
    // The step 3 is the color itself: the others are computed, as for any color, and stay within a
    // few units of the official ones on every channel
    const channels = (hex: string) => [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16));
    const computed = computePalette("#0978CE");
    for (const [scale, official] of [[computed.primary, OFFICIAL_PRIMARY], [computed.neutral, OFFICIAL_NEUTRAL]] as const) {
      scale.forEach((color, i) => {
        channels(color).forEach((value, c) => {
          expect(Math.abs(value - (channels(official[i] as string)[c] as number)), `${color} for ${official[i]}`).to.be.at.most(6);
        });
      });
    }
  });

  it("keeps the exact color only where it meets the minimums of its step", () => {
    const green = computePalette("#2E7D32");
    expect(green.step).to.eq(2);
    expect(green.exact).to.eq(true);
    expect(green.primary[2]).to.eq("#2E7D32");

    // #E65100 is closest to the step 3, and fails 4.5:1 on white
    const orange = computePalette("#E65100");
    expect(contrast("#E65100", FIXED_COLORS.white)).to.be.lessThan(4.5);
    expect(orange.step).to.eq(2);
    expect(orange.exact).to.eq(false);
    expect(orange.primary[2]).not.to.eq("#E65100");

    // #C2185B, 5.9:1 on white, is closest to the step 4, the link and the button, and fails 7:1
    const pink = computePalette("#C2185B");
    expect(pink.step).to.eq(3);
    expect(pink.exact).to.eq(false);

    // #A0124F, 7.8:1 on white, is the step 4 as it is
    const magenta = computePalette("#A0124F");
    expect(magenta.step).to.eq(3);
    expect(magenta.exact).to.eq(true);
  });

  it("never makes the brand the subtle surface", () => {
    // A light color is the step 2, the link of the dark theme: the step 1 stays a tint
    const yellow = computePalette("#FFD600");
    expect(yellow.step).to.eq(1);
    expect(yellow.exact).to.eq(true);
    expect(contrast(yellow.primary[0] as string, FIXED_COLORS.white)).to.be.lessThan(1.2);

    // The white would be lighter than the tint: the scale takes the closest color in its place
    const white = computePalette("#FFFFFF");
    expect(white.step).to.eq(1);
    expect(white.exact).to.eq(false);
  });

  it("ends the neutral scale with the black", () => {
    for (const color of COLORS) {
      expect(computePalette(color).neutral[4]).to.eq(FIXED_COLORS.black);
    }
  });

  it("meets every minimum for any color", () => {
    for (const color of COLORS) {
      const palette = computePalette(color);
      // Each primary step meets its own minimums on the white and on the black
      MINIMUMS.forEach((minimum, i) => {
        const step = palette.primary[i] as string;
        expect(contrast(step, FIXED_COLORS.white), `${color}: step ${i + 1} on white`).to.be.at.least(minimum.white ?? 1);
        expect(contrast(step, FIXED_COLORS.black), `${color}: step ${i + 1} on black`).to.be.at.least(minimum.black ?? 1);
      });
      // The button of the dark theme on its black background
      expect(contrast(palette.primary[2] as string, FIXED_COLORS.black), `${color}: step 3 on black`).to.be.at.least(3);
      expect(MINIMUMS).to.have.length(5);

      // The neutral steps meet their own minimums
      NEUTRAL_MINIMUMS.forEach((minimum, i) => {
        const step = palette.neutral[i] as string;
        expect(contrast(step, FIXED_COLORS.white), `${color}: neutral ${i + 1} on white`).to.be.at.least(minimum.white ?? 1);
        expect(contrast(step, FIXED_COLORS.black), `${color}: neutral ${i + 1} on black`).to.be.at.least(minimum.black ?? 1);
      });

      // Every text pair is AAA (7:1). The link and the button of the light theme, under their white
      // label and pointed
      expect(contrast(palette.primary[3] as string, FIXED_COLORS.white), `${color}: link on white`).to.be.at.least(7);
      expect(contrast(palette.primary[4] as string, FIXED_COLORS.white), `${color}: button pointed`).to.be.at.least(7);
      // The link and the button of the dark theme, under their black label and pointed
      expect(contrast(palette.primary[1] as string, FIXED_COLORS.black), `${color}: link on black`).to.be.at.least(7);
      expect(contrast(palette.primary[0] as string, FIXED_COLORS.black), `${color}: dark button pointed`).to.be.at.least(7);
      // The links of the subtle surfaces: Brand_2 on Blue_1 and Gray_1, Blue_2 on Brand_2
      expect(contrast(palette.primary[4] as string, palette.primary[0] as string), `${color}: link on the step 1`).to.be.at.least(7);
      expect(contrast(palette.primary[4] as string, palette.neutral[0] as string), `${color}: link on the footer`).to.be.at.least(7);
      expect(contrast(palette.primary[1] as string, palette.primary[4] as string), `${color}: link on the step 5`).to.be.at.least(7);
      expect(contrast(palette.neutral[0] as string, palette.primary[4] as string), `${color}: text on the step 5`).to.be.at.least(7);

      // The ring of the focus, on every background it can stand on: Brand_2 in the light theme,
      // the step 2 in the dark one and on the black band
      expect(contrast(palette.primary[4] as string, FIXED_COLORS.white), `${color}: focus on white`).to.be.at.least(3);
      expect(contrast(palette.primary[4] as string, palette.primary[0] as string), `${color}: focus on the step 1`).to.be.at.least(3);
      expect(contrast(palette.primary[1] as string, FIXED_COLORS.black), `${color}: focus on black`).to.be.at.least(3);
      expect(contrast(palette.primary[1] as string, palette.primary[4] as string), `${color}: focus on the step 5`).to.be.at.least(3);

      // The outlines of the dark theme: the cards (neutral 3) and the subtle surfaces (primary 3)
      expect(contrast(palette.neutral[2] as string, FIXED_COLORS.black), `${color}: card border on black`).to.be.at.least(3);
    }
  });

  it("goes from the lightest to the darkest step", () => {
    for (const color of COLORS) {
      const palette = computePalette(color);
      for (const scale of [palette.primary, palette.neutral]) {
        for (let i = 1; i < scale.length; i++) {
          expect(contrast(scale[i] as string, FIXED_COLORS.white), `${color} step ${i}`).to.be.greaterThan(contrast(scale[i - 1] as string, FIXED_COLORS.white));
        }
      }
    }
  });

  it("is the same palette at every computation", () => {
    for (const color of COLORS) {
      expect(computePalette(color)).to.deep.eq(computePalette(color));
    }
  });

  it("reads a color typed as #RRGGBB or RRGGBB in any case", () => {
    expect(normalizeHexColor("#0978cf")).to.eq("#0978CF");
    expect(normalizeHexColor("0978CF")).to.eq("#0978CF");
    expect(normalizeHexColor(" 2e7d32 ")).to.eq("#2E7D32");
    for (const text of ["", "#0978C", "#0978CFF", "##0978CF", "#GGGGGG", "red", "rgb(0, 0, 0)"]) {
      expect(normalizeHexColor(text), text).to.eq(null);
    }
  });
});

describe("theme", () => {
  afterEach(() => {
    emulate([]);
  });

  it("takes the primary color the administrator chooses with the picker", () => {
    cy.login_admin();
    cy.visit("#/admin/settings");

    cy.get("#primary-color").should("have.value", "#0978cf");
    cy.get("#reset-primary-color").should("be.disabled");

    cy.get("#pick-primary-color .primary-color-value").should("have.text", "#0978CF");

    // The button of the picker shows the color as it is chosen, and nothing else
    cy.get("#primary-color").invoke("val", "#2e7d32").trigger("input");
    cy.get("#pick-primary-color .primary-color-value").should("have.text", "#2E7D32");
    cy.get("#PrimaryColor .palette-swatch").should("not.exist");

    // Nothing reaches the site before the save
    expectRoot("--gl-primary-3", "#0978CF");

    cy.intercept("PUT", "**/api/admin/node").as("saveNode");
    cy.get("#save_settings").click();
    cy.wait("@saveNode").its("request.body.primary_color").should("eq", "#2E7D32");

    const green = computePalette("#2E7D32");
    expectRoot("--gl-primary-3", "#2E7D32");
    expectRoot("--gl-button", green.primary[3] as string);
    cy.logout();
  });

  it("keeps the color chosen, and colors the site with the closest accessible one", () => {
    cy.login_admin();
    cy.visit("#/admin/settings");

    // #C2185B fails the 7:1 of its step: the picker keeps it as it is, and says nothing of it
    cy.get("#primary-color").invoke("val", "#c2185b").trigger("input");
    cy.get("#pick-primary-color .primary-color-value").should("have.text", "#C2185B");

    cy.intercept("PUT", "**/api/admin/node").as("saveNode");
    cy.get("#save_settings").click();
    cy.wait("@saveNode").its("response.body.primary_color").should("eq", "#C2185B");

    // The site takes the palette computed from it, where the color itself is not
    const pink = computePalette("#C2185B");
    expectRoot(`--gl-primary-${pink.step + 1}`, pink.primary[pink.step] as string);
    cy.document().should(doc => {
      expect(getComputedStyle(doc.documentElement).getPropertyValue(`--gl-primary-${pink.step + 1}`).trim().toUpperCase()).not.to.eq("#C2185B");
    });

    // The color of the next tests, which the palette keeps as it is
    cy.get("#primary-color").invoke("val", "#a0124f").trigger("input");
    cy.get("#save_settings").click();
    cy.wait("@saveNode").its("response.body.primary_color").should("eq", "#A0124F");
    cy.logout();
  });

  it("colors the pages of who reports with it, in the light and in the dark theme", () => {
    const magenta = computePalette("#A0124F");

    emulate([{name: "prefers-color-scheme", value: "light"}]);
    cy.visit("/");
    expectRoot(`--gl-primary-${magenta.step + 1}`, "#A0124F");
    expectRoles({"--gl-button": magenta.primary[3] as string, "--gl-button-hover": magenta.primary[4] as string, "--gl-link": magenta.primary[3] as string, "--gl-header": "#FFF"});

    emulate([{name: "prefers-color-scheme", value: "dark"}]);
    expectRoles({"--gl-button": magenta.primary[1] as string, "--gl-link": magenta.primary[1] as string, "--gl-header": "#1F1F1F", "--gl-surface-subtle": magenta.primary[4] as string});
  });

  it("colors the pages of the recipients with it, in the theme each switches to for the session", () => {
    const magenta = computePalette("#A0124F");

    emulate([{name: "prefers-color-scheme", value: "light"}]);
    cy.login_receiver();
    cy.get("html").should("not.have.attr", "data-theme");
    expectRoles({"--gl-button": magenta.primary[3] as string, "--gl-text-secondary": magenta.neutral[3] as string});

    // The switch is the only place of the choice: the preferences do not offer it
    cy.visit("/#/recipient/preferences");
    cy.get("#PreferencesForm").should("be.visible");
    cy.get("#pref-theme-select").should("not.exist");

    // The choice wins over the system for the session, and is never kept in the account
    cy.intercept("PUT", "**/api/user/preferences").as("savePreferences");
    cy.get("#ThemeToggle").click();
    cy.get("html").should("have.attr", "data-theme", "dark");
    expectRoles({"--gl-link": magenta.primary[1] as string, "--gl-text": magenta.neutral[0] as string});

    cy.get("#ThemeToggle").click();
    cy.get("html").should("have.attr", "data-theme", "light");
    cy.get("html").should("have.attr", "data-bs-theme", "light");
    expectRoles({"--gl-link": magenta.primary[3] as string, "--gl-bg": "#FFF"});
    cy.get("@savePreferences.all").should("have.length", 0);

    // A new session follows the system again
    cy.logout();
    emulate([{name: "prefers-color-scheme", value: "dark"}]);
    cy.window().then(win => win.sessionStorage.clear());
    cy.reload();
    cy.login_receiver();
    cy.get("html").should("not.have.attr", "data-theme");
    cy.get("html").should("have.attr", "data-bs-theme", "dark");
    cy.logout();
  });

  it("stays readable in forced colors and stronger in increased contrast", () => {
    emulate([{name: "prefers-contrast", value: "more"}, {name: "prefers-color-scheme", value: "light"}]);
    cy.visit("/");
    const magenta = computePalette("#A0124F");
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

  it("goes back to the GlobaLeaks default", () => {
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
  });
});
