import {Injectable, inject, signal} from "@angular/core";
import {RenderSchedulerService} from "@app/shared/services/render-scheduler.service";

export type Theme = "light" | "dark";

const STORAGE_KEY = "theme";

/**
 * The theme of the interface
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

  // The theme chosen with the switch; null following the browser
  private chosenTheme: Theme | null = ThemeService.readChoice();

  // The theme shown, for the components drawing something of their own for it (the logo)
  readonly theme = signal<Theme>("light");

  constructor() {
    this.media.addEventListener("change", () => this.apply());
    this.apply();
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
