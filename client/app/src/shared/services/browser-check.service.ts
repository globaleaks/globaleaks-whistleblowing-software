import {Injectable} from "@angular/core";

@Injectable({
  providedIn: "root",
})
export class BrowserCheckService {
  constructor() {
  }

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

    for (let i=0; i < crawlers.length; i++) {
      if (navigator.userAgent.indexOf(crawlers[i]) !== -1) {
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
