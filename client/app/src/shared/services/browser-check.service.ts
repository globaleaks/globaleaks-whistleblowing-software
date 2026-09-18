import {Injectable} from "@angular/core";

@Injectable({
  providedIn: "root",
})
export class BrowserCheckService {
  checkBrowserSupport(): boolean {
    const crawlers = [
      "Googlebot",
      "Bingbot",
      "Slurp",
      "DuckDuckBot",
      "Baiduspider",
      "YandexBot",
      "Sogou",
      "Exabot",
      "ia_archiver"
    ];

    for (const crawler of crawlers) {
      if (navigator.userAgent.indexOf(crawler) !== -1) {
        return true;
      }
    }

    if (typeof window === "undefined") {
      return false;
    }

    if (!(window.isSecureContext && window.crypto && window.crypto.subtle)) {
      return false;
    }

    if (!(window.File && window.FileList && window.FileReader)) {
      return false;
    }

    if (typeof Blob === "undefined" || !Blob.prototype.slice) {
      return false;
    }

    return true;
  }}
