import {Injectable, inject} from "@angular/core";
import {HttpClient} from "@angular/common/http";
import {TranslateLoader, TranslationObject} from "@ngx-translate/core";
import {Observable, catchError, of, shareReplay, switchMap} from "rxjs";
import {bcp47ToLocale} from "@app/services/helper/locale-provider";

// The language the page will most likely be shown in, known before the public data that confirms
// it, in the order the application chooses it: the one of this session, the one of the URL, and the
// one the backend wrote on the page from the preferences of the browser, or else its default
export function guessLanguage(): string {
  const query = window.location.hash.split("?")[1] || "";

  return sessionStorage.getItem("language") ||
         new URLSearchParams(query).get("lang") ||
         bcp47ToLocale(document.documentElement.lang || "en");
}

// Loads the texts of a language from the backend. The texts of the language the page will most
// likely be shown in are requested together with the public data instead of after it.
@Injectable()
export class TranslationLoader implements TranslateLoader {
  private readonly http = inject(HttpClient);
  private prefetched?: {lang: string; texts: Observable<TranslationObject | null>};

  prefetch(lang: string) {
    const texts = this.http.get<TranslationObject>("l10n/" + encodeURIComponent(lang)).pipe(
      catchError(() => of(null)),
      shareReplay(1)
    );

    texts.subscribe();
    this.prefetched = {lang, texts};
  }

  getTranslation(lang: string): Observable<TranslationObject> {
    const prefetched = this.prefetched;
    this.prefetched = undefined;

    if (prefetched?.lang === lang) {
      return prefetched.texts.pipe(switchMap(texts => texts ? of(texts) : this.load(lang)));
    }

    return this.load(lang);
  }

  private load(lang: string): Observable<TranslationObject> {
    return this.http.get<TranslationObject>("l10n/" + encodeURIComponent(lang)).pipe(
      catchError(() => of({}))
    );
  }
}
