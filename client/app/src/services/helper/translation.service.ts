import {BehaviorSubject} from 'rxjs';
import {Injectable, inject} from "@angular/core";
import {TranslateService} from "@ngx-translate/core";
import {UtilsService} from "@app/shared/services/utils.service";

@Injectable({
  providedIn: "root",
})
export class TranslationService {
  private readonly utilsService = inject(UtilsService);
  protected translate = inject(TranslateService);

  language = "";

  private readonly currentLocale = new BehaviorSubject<string>("");
  currentLocale$ = this.currentLocale.asObservable();

  changeLocale(newLocale: string) {
    this.currentLocale.next(newLocale);
  }

  public currentDirection: string;

  constructor() {
    this.currentDirection = this.utilsService.getDirection(this.translate.getCurrentLang());
  }

  setLanguage(language: string) {
    if (!this.language || this.language != language) {
      this.language = language;
      window.GL.language = this.language;
      sessionStorage.setItem("language", this.language);
      document.documentElement.dir = this.utilsService.getDirection(this.language);
      this.changeLocale(this.language);
      this.translate.use(this.language);
    };
  }
}
