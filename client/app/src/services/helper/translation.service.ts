import {BehaviorSubject} from 'rxjs';
import {Injectable, inject} from "@angular/core";
import {TranslateService} from "@ngx-translate/core";
import {UtilsService} from "@app/shared/services/utils.service";
import {AppDataService} from "@app/app-data.service";

@Injectable({
  providedIn: "root",
})
export class TranslationService {
  private utilsService = inject(UtilsService);
  protected translate = inject(TranslateService);
  private appDataService = inject(AppDataService);

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

  onChange(language: string, callback?: () => void) {
    this.language = language;
    document.documentElement.dir = this.utilsService.getDirection(this.language);
    sessionStorage.setItem("language", this.language);
    this.changeLocale(this.language);
    this.translate.setFallbackLang(this.language);
    this.translate.use(this.language).subscribe(() => {
      this.appDataService.language = this.language
      window.GL.language = this.language
      if (callback) {
        callback();
      }
    });
  }
}
