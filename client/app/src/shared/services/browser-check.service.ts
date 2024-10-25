import {Injectable} from "@angular/core";

@Injectable({
  providedIn: "root",
})
export class BrowserCheckService {
  private supportedBrowsers: { [key: string]: number } = {
    Firefox: 38,
    Chrome: 45,
    Brave: 1.20,
    Edge: 12,
    IE: 11,
    Safari: 8,
    iOS: 9,
    Android: 4.4,
  };


  checkBrowserSupport(): boolean {
    const browser = this.getBrowser();
    const version = this.getBrowserVersion(browser);

    return this.isBrowserSupported(browser, version);
  }

  private getBrowser(): string {
    const userAgent = window.navigator.userAgent;
    if (userAgent.includes("Firefox")) return "Firefox";
    if (userAgent.includes("Chrome")) return "Chrome";
    if (userAgent.includes("Edg")) return "Edge";
    if (userAgent.includes("Safari")) return "Safari";
    if (userAgent.includes("MSIE") || userAgent.includes("Trident/")) return "IE";
    if (userAgent.includes("Brave")) return "Brave";
    if (userAgent.includes("iPhone") || userAgent.includes("iPad")) return "iOS";
    if (userAgent.includes("Android")) return "Android";

    return "Unknown";
  }

  private getBrowserVersion(browser: string): number {
    const userAgent = window.navigator.userAgent;
    const match = userAgent.match(new RegExp(`${browser}/([\\d.]+)`));

    return match ? parseFloat(match[1]) : 0;
  }

  private isBrowserSupported(browser: string, version: number): boolean {
    const minVersion = this.supportedBrowsers[browser];
    return minVersion !== undefined && version >= minVersion;
  }
}
