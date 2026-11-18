// The palette the interface computes from the primary color of the site: pure functions, checked
// with the test runner of Node (node --test tests/) on every color the configurator can give
import {test} from "node:test";
import assert from "node:assert/strict";

import {
  FIXED_COLORS,
  MINIMUMS,
  NEUTRAL_MINIMUMS,
  OFFICIAL_NEUTRAL,
  OFFICIAL_PRIMARY,
  computePalette,
  contrast,
  normalizeHexColor
} from "../app/src/shared/theme/palette.ts";

const hex = (value: number) => Math.round(value * 255).toString(16).padStart(2, "0").toUpperCase();

const hsl = (h: number, s: number, l: number) => {
  const k = (n: number) => (n + h / 30) % 12;
  const a = s * Math.min(l, 1 - l);
  const f = (n: number) => l - a * Math.max(-1, Math.min(k(n) - 3, 9 - k(n), 1));
  return `#${hex(f(0))}${hex(f(8))}${hex(f(4))}`;
};

// Every hue each 5°, the saturation from 10% to 100% and the lightness from 5% to 95%: 13,680
// colors, with the white and the black
const COLORS = ["#FFFFFF", "#000000"];
for (let h = 0; h < 360; h += 5) {
  for (let s = 10; s <= 100; s += 10) {
    for (let l = 5; l <= 95; l += 5) {
      COLORS.push(hsl(h, s / 100, l / 100));
    }
  }
}

const atLeast = (value: number, minimum: number, message: string) =>
  assert.ok(value >= minimum, `${message}: ${value.toFixed(2)} < ${minimum}`);

test("is the official GlobaLeaks palette for the default color", () => {
  const palette = computePalette("#0978CF");
  assert.deepEqual(palette.primary, OFFICIAL_PRIMARY);
  assert.deepEqual(palette.neutral, OFFICIAL_NEUTRAL);
  assert.equal(palette.exact, true);

  // The palette of the Visual Identity Guidelines v3.0
  assert.deepEqual(OFFICIAL_PRIMARY, ["#ECF5FE", "#7BBBFE", "#0978CF", "#025A9F", "#002445"]);
  assert.deepEqual(OFFICIAL_NEUTRAL, ["#F2F4F7", "#A5ACB6", "#6E7783", "#525964", "#1F1F1F"]);
});

test("computes from the official color a palette close to the official one", () => {
  // The step 3 is the color itself: the others are computed, as for any color, and stay within a
  // few units of the official ones on every channel
  const channels = (color: string) => [1, 3, 5].map(i => parseInt(color.slice(i, i + 2), 16));
  const computed = computePalette("#0978CE");
  for (const [scale, official] of [[computed.primary, OFFICIAL_PRIMARY], [computed.neutral, OFFICIAL_NEUTRAL]] as const) {
    scale.forEach((color, i) => {
      channels(color).forEach((value, c) => {
        assert.ok(Math.abs(value - (channels(official[i] as string)[c] as number)) <= 6, `${color} for ${official[i]}`);
      });
    });
  }
});

test("keeps the exact color only where it meets the minimums of its step", () => {
  const green = computePalette("#2E7D32");
  assert.equal(green.step, 2);
  assert.equal(green.exact, true);
  assert.equal(green.primary[2], "#2E7D32");

  // #E65100 is closest to the step 3, and fails 4.5:1 on white
  const orange = computePalette("#E65100");
  assert.ok(contrast("#E65100", FIXED_COLORS.white) < 4.5);
  assert.equal(orange.step, 2);
  assert.equal(orange.exact, false);
  assert.notEqual(orange.primary[2], "#E65100");

  // #C2185B, 5.9:1 on white, is closest to the step 4, the link and the button, and fails 7:1
  const pink = computePalette("#C2185B");
  assert.equal(pink.step, 3);
  assert.equal(pink.exact, false);

  // #A0124F, 7.8:1 on white, is the step 4 as it is
  const magenta = computePalette("#A0124F");
  assert.equal(magenta.step, 3);
  assert.equal(magenta.exact, true);
});

test("never makes the brand the subtle surface", () => {
  // A light color is the step 2, the link of the dark theme: the step 1 stays a tint
  const yellow = computePalette("#FFD600");
  assert.equal(yellow.step, 1);
  assert.equal(yellow.exact, true);
  assert.ok(contrast(yellow.primary[0] as string, FIXED_COLORS.white) < 1.2);

  // The white would be lighter than the tint: the scale takes the closest color in its place
  const white = computePalette("#FFFFFF");
  assert.equal(white.step, 1);
  assert.equal(white.exact, false);
});

test("meets every minimum, in order from the lightest to the darkest step, for any color", () => {
  assert.equal(MINIMUMS.length, 5);

  for (const color of COLORS) {
    const palette = computePalette(color);
    const [p1, p2, p3, p4, p5] = palette.primary as [string, string, string, string, string];
    const [n1, , n3, , n5] = palette.neutral as [string, string, string, string, string];

    // Each step meets its own minimums on the white and on the black
    for (const [scale, minimums, name] of [[palette.primary, MINIMUMS, "step"], [palette.neutral, NEUTRAL_MINIMUMS, "neutral"]] as const) {
      minimums.forEach((minimum, i) => {
        atLeast(contrast(scale[i] as string, FIXED_COLORS.white), minimum.white ?? 1, `${color}: ${name} ${i + 1} on white`);
        atLeast(contrast(scale[i] as string, FIXED_COLORS.black), minimum.black ?? 1, `${color}: ${name} ${i + 1} on black`);
      });
      for (let i = 1; i < scale.length; i++) {
        assert.ok(contrast(scale[i] as string, FIXED_COLORS.white) > contrast(scale[i - 1] as string, FIXED_COLORS.white), `${color}: ${name} ${i + 1} darker`);
      }
    }
    assert.equal(n5, FIXED_COLORS.black, `${color}: the neutral scale ends with the black`);

    // The button of the dark theme on its black background
    atLeast(contrast(p3, FIXED_COLORS.black), 3, `${color}: step 3 on black`);

    // Every text pair is AAA (7:1): the link and the button of the light theme, under their white
    // label and pointed, and those of the dark theme, under their black label and pointed
    atLeast(contrast(p4, FIXED_COLORS.white), 7, `${color}: link on white`);
    atLeast(contrast(p5, FIXED_COLORS.white), 7, `${color}: button pointed`);
    atLeast(contrast(p2, FIXED_COLORS.black), 7, `${color}: link on black`);
    atLeast(contrast(p1, FIXED_COLORS.black), 7, `${color}: dark button pointed`);
    // The links of the subtle surfaces: the step 5 on the step 1 and on the footer, the step 2 on
    // the step 5
    atLeast(contrast(p5, p1), 7, `${color}: link on the step 1`);
    atLeast(contrast(p5, n1), 7, `${color}: link on the footer`);
    atLeast(contrast(p2, p5), 7, `${color}: link on the step 5`);
    atLeast(contrast(n1, p5), 7, `${color}: text on the step 5`);

    // The ring of the focus, on every background it can stand on: the step 5 in the light theme,
    // the step 2 in the dark one and on the black band
    atLeast(contrast(p5, FIXED_COLORS.white), 3, `${color}: focus on white`);
    atLeast(contrast(p5, p1), 3, `${color}: focus on the step 1`);
    atLeast(contrast(p2, FIXED_COLORS.black), 3, `${color}: focus on black`);
    atLeast(contrast(p2, p5), 3, `${color}: focus on the step 5`);

    // The outlines of the cards of the dark theme
    atLeast(contrast(n3, FIXED_COLORS.black), 3, `${color}: card border on black`);
  }
});

test("is the same palette at every computation", () => {
  for (const color of COLORS.filter((_, i) => i % 97 === 0)) {
    assert.deepEqual(computePalette(color), computePalette(color));
  }
});

test("reads a color typed as #RRGGBB or RRGGBB in any case", () => {
  assert.equal(normalizeHexColor("#0978cf"), "#0978CF");
  assert.equal(normalizeHexColor("0978CF"), "#0978CF");
  assert.equal(normalizeHexColor(" 2e7d32 "), "#2E7D32");
  for (const text of ["", "#0978C", "#0978CFF", "##0978CF", "#GGGGGG", "red", "rgb(0, 0, 0)"]) {
    assert.equal(normalizeHexColor(text), null, text);
  }
});
