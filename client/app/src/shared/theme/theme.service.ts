import {Injectable, inject, signal} from "@angular/core";
import {RenderSchedulerService} from "@app/shared/services/render-scheduler.service";
import {OFFICIAL_PRIMARY_COLOR, computePalette, paletteProperties} from "@app/shared/theme/palette";

export type Theme = "light" | "dark";

const STORAGE_KEY = "theme";

/**
 * The colors of the interface: the palette of the primary color of the site and the theme
 *
 * The palette is written as custom properties in a stylesheet built through the CSSOM, which the
 * Content Security Policy allows where it forbids a <style> element or a style attribute. Its
 * rules have no specificity (:where), like the ones of theme.css they replace, so that the custom
 * CSS of the site still overrides them.
 *
 * The theme follows the one of the browser until the user switches it with the switch of the
 * header. The choice is kept in the storage of the session, as the language is: it survives the
 * reloads and the navigation of the tab and is lost with it; nothing about the theme is ever kept
 * on the device beyond the session, nor in the account.
 */
@Injectable({
  providedIn: "root"
})
export class ThemeService {
  private readonly renderScheduler = inject(RenderSchedulerService);

  private readonly media = window.matchMedia("(prefers-color-scheme: dark)");
  private sheet: CSSStyleSheet | null = null;
  private primaryColor: string | null = null;

  // The theme chosen with the switch; null following the browser
  private chosenTheme: Theme | null = ThemeService.readChoice();

  // The theme shown, for the components drawing something of their own for it (the logo)
  readonly theme = signal<Theme>("light");

  constructor() {
    this.media.addEventListener("change", () => this.apply());
    this.apply();
  }

  /**
   * Apply the palette of a primary color
   */
  setPrimaryColor(color: string | null | undefined): void {
    color = color || OFFICIAL_PRIMARY_COLOR;
    if (color === this.primaryColor) {
      return;
    }

    this.primaryColor = color;

    const properties = paletteProperties(computePalette(color));
    const declarations = Object.entries(properties).map(([name, value]) => `${name}: ${value};`).join(" ");

    if (this.sheet === null && "adoptedStyleSheets" in document) {
      this.sheet = new CSSStyleSheet();
      document.adoptedStyleSheets = [...document.adoptedStyleSheets, this.sheet];
    }

    if (this.sheet !== null) {
      this.sheet.replaceSync(`:where(:root) { ${declarations} }`);
    } else {
      for (const [name, value] of Object.entries(properties)) {
        document.documentElement.style.setProperty(name, value);
      }
    }
  }

  /**
   * Switch to the other theme, for as long as the session lives
   */
  toggle(): void {
    this.chosenTheme = this.theme() === "dark" ? "light" : "dark";
    try {
      sessionStorage.setItem(STORAGE_KEY, this.chosenTheme);
    } catch {
      // A storage that refuses the choice leaves it to the page alone
    }
    this.apply();
  }

  private static readChoice(): Theme | null {
    try {
      const value = sessionStorage.getItem(STORAGE_KEY);
      return value === "light" || value === "dark" ? value : null;
    } catch {
      return null;
    }
  }

  private apply(): void {
    const theme: Theme = this.chosenTheme ?? (this.media.matches ? "dark" : "light");
    const root = document.documentElement;

    // Following the system, the stylesheet reads the preference of the system by itself
    if (this.chosenTheme === null) {
      root.removeAttribute("data-theme");
    } else {
      root.setAttribute("data-theme", this.chosenTheme);
    }

    // Bootstrap draws a few things of its own (the arrows of the selects, the close buttons) for
    // the theme it is told
    root.setAttribute("data-bs-theme", theme);

    this.theme.set(theme);
    this.renderScheduler.schedule();
  }
}
