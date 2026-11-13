/**
 * The palette of the interface, computed from one primary color.
 *
 * The palette is the one of the GlobaLeaks Visual Identity Guidelines v3.0: a
 * primary scale of five steps (1 … 5) going from a tint almost white to a shade
 * almost black, each step at a fixed contrast on white, and beside it a neutral
 * scale of the same hue and little chroma, whose darkest step is the black. The
 * light theme reads the scales from the light end, the dark theme from the dark
 * one (theme.css).
 *
 * The primary color takes the step of the brand closest to it, 2 … 5: the step
 * 1 is the subtle surface, a tint and never a brand. The official GlobaLeaks
 * color #0978CF gives the official palette, written here as it is; any other
 * color is computed in the OKLCH color space against the WCAG 2.x relative
 * luminance. The module is pure: the same color always gives the same palette,
 * in the preview of the administrators as on every page.
 */

export const OFFICIAL_PRIMARY_COLOR = "#0978CF";

const STEPS = [1, 2, 3, 4, 5];

export const OFFICIAL_PRIMARY = ["#ECF5FE", "#7BBBFE", "#0978CF", "#025A9F", "#002445"];
export const OFFICIAL_NEUTRAL = ["#F2F4F7", "#A5ACB6", "#6E7783", "#525964", "#1F1F1F"];

// The colors every palette shares, whatever the primary color
export const FIXED_COLORS = {
  white: "#FFFFFF",
  black: "#1F1F1F",
  yellow: "#FFEE33",
  red: "#E30310",
  "red-light": "#FF8F90"
};

// The contrast on white of each step, the one of the official palette
const TARGET_CONTRAST = [1.10, 2.02, 4.57, 7.08, 15.69];
const NEUTRAL_TARGET_CONTRAST = [1.10, 2.28, 4.57, 7.08];

// How much of the chroma of the primary color each step carries, relative to the step 3
const PRIMARY_CHROMA = [0.097, 0.794, 1.0, 0.831, 0.462];

// The chroma of the neutral steps 1 … 4, for a primary color of chroma 0.15; the step 5 is the black
const NEUTRAL_CHROMA = [0.005, 0.016, 0.022, 0.020];

interface Minimum {white?: number; black?: number}

/**
 * The contrast each primary step guarantees on the white and on the black
 * background, by index of the step: what the roles built on it need to be
 * readable.
 *
 *   1  the subtle surface of the light theme, under the black text (7:1 on black);
 *      the button of the dark theme pointed, and the link on its subtle surfaces
 *   2  the link, the button and the focus ring of the dark theme (7:1 on black),
 *      the button under its black label, and the link on its subtle surfaces:
 *      computePalette makes it lighter until it reads at 7:1 on the step 5
 *   3  the brand: accents, icons, borders and large titles of the light theme
 *      (4.5:1 on white), borders and icons of the dark theme (3:1 on black)
 *   4  the link and the button of the light theme, the button under its white
 *      label (7:1 on white)
 *   5  the button of the light theme pointed and its focus ring; the link on the
 *      subtle surface of the light theme, and the band, the footer and the subtle
 *      surfaces of the dark theme: 7:1 with the step 1, that is 10.6:1 on white
 */
export const MINIMUMS: Minimum[] = [
  {black: 7.0},
  {black: 7.0},
  {white: 4.5, black: 3.0},
  {white: 7.0},
  {white: 10.6}
];

/**
 * The contrast each neutral step guarantees: the text (1) and the secondary text
 * (2) of the dark theme, the border of the inputs and of the surfaces of the dark
 * theme (3) and the secondary text of the light theme (4). The step 5 is the black.
 */
export const NEUTRAL_MINIMUMS: Minimum[] = [
  {black: 7.0},
  {black: 7.0},
  {white: 4.5, black: 3.0},
  {white: 7.0}
];

export interface Palette {
  primary: string[];
  neutral: string[];
  // The index of the step the primary color belongs to
  step: number;
  // Whether the primary color itself stands at its step, or only the closest color accessibility allows
  exact: boolean;
}

type RGB = [number, number, number];

// The value at an index the scales are known to have
function at<T>(values: readonly T[], index: number): T {
  const value = values[index];
  if (value === undefined) {
    throw new RangeError(`No step at index ${index}`);
  }
  return value;
}

/**
 * Normalize a color typed as #RRGGBB or RRGGBB, in any case, to #RRGGBB in uppercase
 *
 * @return The normalized color, or null when the text is not a color
 */
export function normalizeHexColor(text: string | null | undefined): string | null {
  const digits = /^#?([0-9a-f]{6})$/i.exec((text ?? "").trim())?.[1];
  return digits ? "#" + digits.toUpperCase() : null;
}

function hexToRgb(hex: string): RGB {
  const value = parseInt(hex.slice(1), 16);
  return [(value >> 16) & 255, (value >> 8) & 255, value & 255];
}

function rgbToHex(rgb: RGB): string {
  return "#" + rgb.map(c => Math.round(Math.min(255, Math.max(0, c))).toString(16).padStart(2, "0")).join("").toUpperCase();
}

function linearRgb(hex: string): RGB {
  const [r, g, b] = hexToRgb(hex);
  return [toLinear(r), toLinear(g), toLinear(b)];
}

function clampRgb([r, g, b]: RGB): RGB {
  return [Math.min(1, Math.max(0, r)), Math.min(1, Math.max(0, g)), Math.min(1, Math.max(0, b))];
}

function toLinear(c: number): number {
  c /= 255;
  return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
}

function fromLinear(c: number): number {
  const v = c <= 0.0031308 ? 12.92 * c : 1.055 * Math.pow(c, 1 / 2.4) - 0.055;
  return v * 255;
}

function luminanceOfLinear(r: number, g: number, b: number): number {
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

/**
 * The WCAG 2.x relative luminance of a color
 */
function luminance(hex: string): number {
  const [r, g, b] = linearRgb(hex);
  return luminanceOfLinear(r, g, b);
}

/**
 * The WCAG 2.x contrast ratio between two colors
 */
export function contrast(a: string, b: string): number {
  const la = luminance(a);
  const lb = luminance(b);
  return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05);
}

function oklchToLinear(l: number, c: number, h: number): RGB {
  const a = c * Math.cos(h);
  const b = c * Math.sin(h);

  const l_ = Math.pow(l + 0.3963377774 * a + 0.2158037573 * b, 3);
  const m_ = Math.pow(l - 0.1055613458 * a - 0.0638541728 * b, 3);
  const s_ = Math.pow(l - 0.0894841775 * a - 1.2914855480 * b, 3);

  return [
    4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_,
    -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_,
    -0.0041960863 * l_ - 0.7034186147 * m_ + 1.7076147010 * s_
  ];
}

function linearToOklch(r: number, g: number, b: number): [number, number, number] {
  const l = Math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b);
  const m = Math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b);
  const s = Math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b);

  const L = 0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s;
  const A = 1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s;
  const B = 0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s;

  return [L, Math.sqrt(A * A + B * B), Math.atan2(B, A)];
}

function inGamut(rgb: RGB): boolean {
  return rgb.every(c => c >= -1e-6 && c <= 1 + 1e-6);
}

// The largest chroma of the given lightness and hue that sRGB can show
function maxChroma(l: number, h: number): number {
  let lo = 0;
  let hi = 0.4;
  for (let i = 0; i < 30; i++) {
    const mid = (lo + hi) / 2;
    if (inGamut(oklchToLinear(l, mid, h))) {
      lo = mid;
    } else {
      hi = mid;
    }
  }
  return lo;
}

function oklchToHex(l: number, c: number, h: number): string {
  const [r, g, b] = clampRgb(oklchToLinear(l, Math.min(c, 0.98 * maxChroma(l, h)), h));
  return rgbToHex([fromLinear(r), fromLinear(g), fromLinear(b)]);
}

function linearLuminanceOf(l: number, c: number, h: number): number {
  const [r, g, b] = clampRgb(oklchToLinear(l, Math.min(c, 0.98 * maxChroma(l, h)), h));
  return luminanceOfLinear(r, g, b);
}

// The lightness at which the color of the given chroma and hue reaches the luminance y
function lightnessFor(y: number, c: number, h: number): number {
  let lo = 0;
  let hi = 1;
  for (let i = 0; i < 40; i++) {
    const mid = (lo + hi) / 2;
    if (linearLuminanceOf(mid, c, h) < y) {
      lo = mid;
    } else {
      hi = mid;
    }
  }
  return (lo + hi) / 2;
}

function meets(minimum: Minimum, hex: string): boolean {
  return (minimum.white === undefined || contrast(hex, FIXED_COLORS.white) >= minimum.white) &&
         (minimum.black === undefined || contrast(hex, FIXED_COLORS.black) >= minimum.black);
}

// Generate a step and nudge its lightness until, rounded, it meets the minimum of the step
function generateStep(index: number, minimum: Minimum, c: number, h: number, targets = TARGET_CONTRAST): string {
  const y = 1.05 / at(targets, index) - 0.05;
  let l = lightnessFor(y, c, h);
  let hex = oklchToHex(l, c, h);

  for (let i = 0; !meets(minimum, hex) && i < 200; i++) {
    // Too light for the white background, otherwise too dark for the black one
    const darker = minimum.white !== undefined && contrast(hex, FIXED_COLORS.white) < minimum.white;
    l += darker ? -0.001 : 0.001;
    hex = oklchToHex(l, c, h);
  }

  return hex;
}

// Make a step lighter, keeping its chroma and hue, until it passes the test
function lightenUntil(hex: string, c: number, h: number, test: (candidate: string) => boolean): string {
  let [l] = linearToOklch(...linearRgb(hex));
  let candidate = hex;
  for (let i = 0; !test(candidate) && i < 1000; i++) {
    l += 0.001;
    candidate = oklchToHex(l, c, h);
  }
  return candidate;
}

/**
 * The index of the step a color belongs to: among the steps of the brand (2 … 5), the one whose
 * contrast on white is the closest
 */
function stepOf(hex: string): number {
  const own = contrast(hex, FIXED_COLORS.white);
  let best = 1;
  for (let i = 2; i < TARGET_CONTRAST.length; i++) {
    if (Math.abs(Math.log(own / at(TARGET_CONTRAST, i))) < Math.abs(Math.log(own / at(TARGET_CONTRAST, best)))) {
      best = i;
    }
  }
  return best;
}

/**
 * Compute the palette of a primary color
 *
 * @param color The primary color, #RRGGBB
 * @return The primary and the neutral scale, the step of the color and whether it is kept exactly
 */
export function computePalette(color: string): Palette {
  const hex = normalizeHexColor(color) ?? OFFICIAL_PRIMARY_COLOR;

  if (hex === OFFICIAL_PRIMARY_COLOR) {
    return {primary: [...OFFICIAL_PRIMARY], neutral: [...OFFICIAL_NEUTRAL], step: 2, exact: true};
  }

  const [r, g, b] = linearRgb(hex);
  const [, c0, h] = linearToOklch(r, g, b);
  const k = stepOf(hex);

  const primary = PRIMARY_CHROMA.map((profile, i) => generateStep(i, at(MINIMUMS, i), (c0 / at(PRIMARY_CHROMA, k)) * profile, h));

  // A gray has no hue to lend: its neutral scale stays gray
  const neutralFactor = c0 < 0.002 ? 0 : Math.min(1, Math.max(0.35, c0 / 0.15));
  const neutral = NEUTRAL_CHROMA.map((chroma, i) => generateStep(i, at(NEUTRAL_MINIMUMS, i), chroma * neutralFactor, h, NEUTRAL_TARGET_CONTRAST));
  neutral.push(FIXED_COLORS.black);

  // The color stands at its step where it meets the minimum of the step and keeps the scale going
  // from the lightest to the darkest step
  const own = contrast(hex, FIXED_COLORS.white);
  const ordered = (k === 0 || own > contrast(at(primary, k - 1), FIXED_COLORS.white)) &&
                  (k === primary.length - 1 || own < contrast(at(primary, k + 1), FIXED_COLORS.white));
  let exact = ordered && meets(at(MINIMUMS, k), hex);
  if (exact) {
    primary[k] = hex;
  }

  // The step 2 is also the link on the subtle surfaces of the dark theme (step 5): it gets lighter
  // until it reads at 7:1 on them
  const step2 = lightenUntil(at(primary, 1), (c0 / at(PRIMARY_CHROMA, k)) * at(PRIMARY_CHROMA, 1), h,
                             candidate => contrast(candidate, at(primary, 4)) >= 7);
  if (step2 !== primary[1]) {
    primary[1] = step2;
    exact = exact && k !== 1;
  }

  return {primary, neutral, step: k, exact};
}

/**
 * The custom properties carrying a palette: --gl-primary-1 … 5, --gl-neutral-1 … 5
 */
export function paletteProperties(palette: Palette): Record<string, string> {
  const properties: Record<string, string> = {};
  STEPS.forEach((step, i) => {
    properties[`--gl-primary-${step}`] = at(palette.primary, i);
    properties[`--gl-neutral-${step}`] = at(palette.neutral, i);
  });
  return properties;
}
