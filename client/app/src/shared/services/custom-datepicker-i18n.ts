import {Injectable} from "@angular/core";
import {TranslationService} from "@app/services/helper/translation.service";
import {NgbDatepickerI18n, NgbDateStruct} from '@ng-bootstrap/ng-bootstrap';


@Injectable()
export class CustomDatepickerI18n extends NgbDatepickerI18n {
  private locale: string;

  constructor(private translationService: TranslationService) {
    super();
    this.translationService.currentLocale$.subscribe(locale => {
      this.locale = locale;
    });
  }

  getMonthShortName(month: number): string {
    return new Intl.DateTimeFormat(this.locale, { month: 'short' }).format(new Date(0, month - 1));
  }

  getWeekdayShortName(weekday: number): string {
    return new Intl.DateTimeFormat(this.locale, { weekday: 'short' }).format(new Date(2023, 0, weekday));
  }

  getMonthFullName(month: number): string {
    return new Intl.DateTimeFormat(this.locale, { month: 'long' }).format(new Date(0, month - 1));
  }

  getWeekdayLabel(weekday: number): string {
    return new Intl.DateTimeFormat(this.locale, { weekday: 'short' }).format(new Date(2023, 0, weekday));
  }

  getDayAriaLabel(date: NgbDateStruct): string {
    return `${date.day}-${date.month}-${date.year}`;
  }
}
