import {BehaviorSubject} from 'rxjs';
import {Injectable, Renderer2, inject} from "@angular/core";
import {LangChangeEvent, TranslateService} from "@ngx-translate/core";
import {UtilsService} from "@app/shared/services/utils.service";
import {DOCUMENT} from "@angular/common";

@Injectable({
  providedIn: "root",
})
export class TranslationService {
  private utilsService = inject(UtilsService);
  protected translate = inject(TranslateService);
  private document = inject<Document>(DOCUMENT);

  language = "";

  private currentLocale = new BehaviorSubject<string>("");
  currentLocale$ = this.currentLocale.asObservable();

  changeLocale(newLocale: string) {
    this.currentLocale.next(newLocale);
  }

  public currentDirection: string;

  constructor() {
    this.currentDirection = this.utilsService.getDirection(this.translate.currentLang);
  }

  onChange(changedLanguage: string, callback?: () => void) {
    this.language = changedLanguage;
    this.changeLocale(this.language);
    this.translate.use(this.language).subscribe(() => {
      if (callback) {
        callback();
      }
    });
  }
}
